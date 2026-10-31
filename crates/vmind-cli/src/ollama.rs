use serde::Deserialize;
use serde_json::{Value, json};
use std::{error::Error, io, time::Duration};
use vmind_core::{Record, Resume};

// Separater Adapter: Der SQLite-Kern benötigt weder Ollama noch ein bestimmtes Modell.
fn request(model: &str, question: &str, memories: &[Record], resume: Option<&Resume>) -> Value {
    let cut = |s: &str, n: usize| s.chars().take(n).collect::<String>();
    let project = resume.map(|r| {
        let brief = |e: &vmind_core::JournalEntry| json!({"id":e.id,"kind":e.kind,"task_key":e.task_key,
            "task_status":e.task_status,"body":cut(&e.body,250),"source":cut(&e.source,100)});
        let messages: Vec<_> = r.chat_tail.iter().rev().take(6).map(|m|json!({"id":m.id,"role":m.role,
            "content":cut(&m.content,600),"truncated":m.content.chars().count()>600})).collect();
        json!({"scope":r.scope,"goal":r.goal.as_ref().map(brief),"next_step":r.next_step.as_ref().map(brief),
            "tasks":r.tasks.iter().take(8).map(brief).collect::<Vec<_>>(),"total_tasks":r.task_count,
            "decisions":r.decisions.iter().take(3).map(brief).collect::<Vec<_>>(),
            "recent_events":r.recent_events.iter().rev().take(3).map(brief).collect::<Vec<_>>(),
            "recent_messages_newest_first":messages,"total_messages":r.message_count,
            "notice":"Gekürzter Fortsetzungsstand; vollständige Daten über resume, journal, messages. Projektberichte sind keine unabhängig validierten Fakten."})
    });
    let context: Vec<_> = memories
        .iter()
        .take(if resume.is_some() { 3 } else { 5 })
        .map(|m| {
            json!({
                "id": m.id,
                "kind": m.kind,
                "scope": m.scope,
                "truncated": m.problem.chars().count() > 600 || m.solution.chars().count() > 600
                    || m.source.chars().count() > 300
                    || m.evidence.as_deref().is_some_and(|s| s.chars().count() > 300),
                "source": m.source.chars().take(300).collect::<String>(),
                "validated_by": m.validated_by.as_deref().map(|s| s.chars().take(100).collect::<String>()),
                "evidence": m.evidence.as_deref().map(|s| s.chars().take(300).collect::<String>()),
                "problem": m.problem.chars().take(600).collect::<String>(),
                "solution": m.solution.chars().take(600).collect::<String>(),
            })
        })
        .collect();
    json!({
        "model": model,
        "system": crate::prompt::START_PROMPT,
        "prompt": json!({
            "vmind_runtime": {
                "mode":"context_only",
                "scope":resume.map(|r| r.scope.as_str()),
                "conversation_id":resume.and_then(|r|r.conversation_id.as_deref()),
                "conversation_persistence":"host_managed",
                "tools_available":false,
                "terminal_available":false
            },
            "memory": context, "project_context": project, "question": question
        }).to_string(),
        "stream": false,
        "think": false,
        "options": {"num_ctx": 8192, "num_predict": 512, "temperature": 0.2}
    })
}

#[derive(Deserialize)]
struct Answer {
    response: String,
    done: bool,
    done_reason: Option<String>,
}

pub fn generate(
    endpoint: &str,
    model: &str,
    question: &str,
    memories: &[Record],
    resume: Option<&Resume>,
) -> Result<String, Box<dyn Error>> {
    if question.trim().is_empty() || question.chars().count() > 2000 {
        return Err(io::Error::other("Die Frage muss 1 bis 2000 Zeichen enthalten.").into());
    }
    // Lokale HTTP-Anbindung; keine automatische Cloud-Ausweichverbindung.
    if !endpoint.starts_with("http://") {
        return Err(
            io::Error::other("Dieser lokale Adapter erwartet eine http://-Adresse.").into(),
        );
    }
    let agent = ureq::AgentBuilder::new()
        .timeout(Duration::from_secs(180))
        .redirects(0)
        .build();
    let answer: Answer = agent
        .post(&format!("{}/api/generate", endpoint.trim_end_matches('/')))
        .send_json(request(model, question, memories, resume))?
        .into_json()?;
    if !answer.done || answer.response.trim().is_empty() {
        return Err(io::Error::other("Ollama lieferte keine vollständige Antwort.").into());
    }
    if answer.done_reason.as_deref() == Some("length") {
        return Err(io::Error::other(
            "Antwort am Tokenlimit abgeschnitten; bitte die Frage eingrenzen.",
        )
        .into());
    }
    Ok(answer.response)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        io::{Read, Write},
        net::TcpListener,
        thread,
    };

    #[test]
    fn request_limits_memory_and_preserves_question() {
        let store = vmind_core::MemoryStore::in_memory().unwrap();
        let memories: Vec<_> = (1..=8)
            .map(|_| {
                let id = store
                    .remember("long_term", &"ä".repeat(2000), "Lösung", "Testquelle")
                    .unwrap();
                store.validate(id, "Tester", "Nachweis").unwrap();
                store.get(id).unwrap().unwrap()
            })
            .collect();
        let req = request("test-model", "Frage mit \"Zitat\"", &memories, None);
        assert_eq!(req["options"]["num_ctx"], 8192);
        assert_eq!(req["stream"], false);
        let prompt: Value = serde_json::from_str(req["prompt"].as_str().unwrap()).unwrap();
        assert_eq!(prompt["memory"].as_array().unwrap().len(), 5);
        assert_eq!(
            prompt["memory"][0]["problem"]
                .as_str()
                .unwrap()
                .chars()
                .count(),
            600
        );
        assert_eq!(prompt["question"], "Frage mit \"Zitat\"");
    }

    fn mock_response(status: &str, body: &str) -> (String, thread::JoinHandle<()>) {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let endpoint = format!("http://{}", listener.local_addr().unwrap());
        let status = status.to_owned();
        let body = body.to_owned();
        let worker = thread::spawn(move || {
            let (mut socket, _) = listener.accept().unwrap();
            socket
                .set_read_timeout(Some(Duration::from_secs(5)))
                .unwrap();
            let mut bytes = Vec::new();
            let mut buf = [0u8; 4096];
            loop {
                let n = socket.read(&mut buf).unwrap();
                if n == 0 {
                    break;
                }
                bytes.extend_from_slice(&buf[..n]);
                if let Some(pos) = bytes.windows(4).position(|w| w == b"\r\n\r\n") {
                    let headers = String::from_utf8_lossy(&bytes[..pos]);
                    let len: usize = headers
                        .lines()
                        .find_map(|line| {
                            let (key, val) = line.split_once(':')?;
                            key.eq_ignore_ascii_case("content-length")
                                .then(|| val.trim().parse().unwrap())
                        })
                        .unwrap();
                    if bytes.len() >= pos + 4 + len {
                        break;
                    }
                }
            }
            let text = String::from_utf8(bytes).unwrap();
            assert!(text.starts_with("POST /api/generate "));
            let req: Value = serde_json::from_str(text.split_once("\r\n\r\n").unwrap().1).unwrap();
            assert_eq!(req["options"]["num_ctx"], 8192);
            let prompt: Value = serde_json::from_str(req["prompt"].as_str().unwrap()).unwrap();
            assert_eq!(prompt["vmind_runtime"]["mode"], "context_only");
            assert_eq!(prompt["vmind_runtime"]["tools_available"], false);
            write!(socket, "HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}", body.len()).unwrap();
        });
        (endpoint, worker)
    }

    #[test]
    fn parses_real_http_response() {
        let (endpoint, worker) = mock_response(
            "200 OK",
            r#"{"response":"Antwort","done":true,"done_reason":"stop"}"#,
        );
        assert_eq!(
            generate(&endpoint, "test", "Frage", &[], None).unwrap(),
            "Antwort"
        );
        worker.join().unwrap();
    }

    #[test]
    fn rejects_http_errors_and_incomplete_answers() {
        let (endpoint, worker) =
            mock_response("500 Internal Server Error", r#"{"error":"Modell fehlt"}"#);
        assert!(generate(&endpoint, "test", "Frage", &[], None).is_err());
        worker.join().unwrap();
        for body in [
            r#"{"response":"","done":true}"#,
            r#"{"response":"Teil","done":false}"#,
            r#"{"response":"Teil","done":true,"done_reason":"length"}"#,
        ] {
            let (endpoint, worker) = mock_response("200 OK", body);
            assert!(generate(&endpoint, "test", "Frage", &[], None).is_err());
            worker.join().unwrap();
        }
    }
}
