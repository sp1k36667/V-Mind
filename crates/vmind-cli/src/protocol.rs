//! Ein JSON-Objekt pro Zeile über stdin/stdout; eigenes Protokoll v1, kein MCP.
use serde::Deserialize;
use serde_json::{Value, json};
use std::io::{self, BufRead, Read, Write};
use vmind_core::MemoryStore;

fn global() -> String {
    "global".into()
}
fn five() -> usize {
    5
}

#[derive(Deserialize)]
#[serde(tag = "op", rename_all = "snake_case", deny_unknown_fields)]
enum Operation {
    Recall {
        query: String,
        #[serde(default = "global")]
        scope: String,
        #[serde(default = "five")]
        limit: usize,
    },
    Get {
        memory_id: i64,
    },
    Propose {
        kind: String,
        problem: String,
        solution: String,
        source: String,
        #[serde(default = "global")]
        scope: String,
    },
    Pending {
        #[serde(default = "global")]
        scope: String,
    },
    Stats {
        #[serde(default = "global")]
        scope: String,
    },
    Resume {
        scope: String,
        #[serde(default)]
        conversation_id: Option<String>,
    },
    Journal {
        scope: String,
        #[serde(default)]
        after: i64,
        #[serde(default = "five")]
        limit: usize,
    },
    Log {
        scope: String,
        kind: String,
        #[serde(default)]
        task_key: Option<String>,
        #[serde(default)]
        task_status: Option<String>,
        body: String,
        source: String,
    },
    SessionNew {
        scope: String,
        title: String,
    },
    Sessions {
        scope: String,
    },
    Message {
        conversation_id: String,
        role: String,
        content: String,
    },
    Messages {
        conversation_id: String,
        #[serde(default)]
        after: i64,
        #[serde(default = "five")]
        limit: usize,
    },
    Describe,
}

pub fn dispatch(store: &MemoryStore, mut value: Value) -> Value {
    let id = value
        .as_object_mut()
        .and_then(|v| v.remove("id"))
        .unwrap_or(Value::Null);
    let result = (|| -> Result<Value, Box<dyn std::error::Error>> {
        let op: Operation = serde_json::from_value(value)?;
        Ok(match op {
            Operation::Recall {
                query,
                scope,
                limit,
            } => json!({"memories": store.recall(&query, &scope, limit)?}),
            Operation::Get { memory_id } => {
                json!({"memory": store.get(memory_id)?, "history":store.history(memory_id)?})
            }
            Operation::Propose {
                kind,
                problem,
                solution,
                source,
                scope,
            } => {
                let memory_id =
                    store.remember_scoped(&scope, &kind, &problem, &solution, &source)?;
                json!({"memory_id":memory_id,"status":"pending"})
            }
            Operation::Pending { scope } => json!({"memories":store.pending(&scope)?}),
            Operation::Stats { scope } => serde_json::to_value(store.stats(&scope)?)?,
            Operation::Resume {
                scope,
                conversation_id,
            } => serde_json::to_value(store.resume(&scope, conversation_id.as_deref())?)?,
            Operation::Journal {
                scope,
                after,
                limit,
            } => json!({"events":store.journal_page(&scope,after,limit)?}),
            Operation::Log {
                scope,
                kind,
                task_key,
                task_status,
                body,
                source,
            } => {
                json!({"event_id":store.journal(&scope,&kind,task_key.as_deref(),task_status.as_deref(),&body,&source)?})
            }
            Operation::SessionNew { scope, title } => {
                json!({"conversation_id":store.create_conversation(&scope,&title)?})
            }
            Operation::Sessions { scope } => json!({"conversations":store.conversations(&scope)?}),
            Operation::Message {
                conversation_id,
                role,
                content,
            } => json!({"message_id":store.append_message(&conversation_id,&role,&content)?}),
            Operation::Messages {
                conversation_id,
                after,
                limit,
            } => json!({"messages":store.messages(&conversation_id,after,limit)?}),
            Operation::Describe => json!({"protocol":"vmind-jsonl", "version":1,
                "operations":["describe", "recall", "get", "propose", "pending", "stats", "resume", "journal", "log", "session_new", "sessions", "message", "messages"],
                "default_scope":"global", "recall_includes_global":true,
                "proposals_require_external_validation":true,
                "validation":"CLI validate; no validation operation in this protocol"}),
        })
    })();
    match result {
        Ok(data) => json!({"id":id,"ok":true,"data":data}),
        Err(error) => json!({"id":id,"ok":false,"error":error.to_string()}),
    }
}

pub(crate) enum Line {
    Eof,
    TooLong,
    Data(Vec<u8>),
}

/// Liest eine Eingabezeile von höchstens 1 MiB; gilt für JSONL und MCP.
pub(crate) fn read_line(input: &mut impl BufRead) -> io::Result<Line> {
    const MAX: u64 = 1_048_576;
    let mut line = Vec::new();
    let n = Read::by_ref(input)
        .take(MAX + 1)
        .read_until(b'\n', &mut line)?;
    Ok(match n {
        0 => Line::Eof,
        n if n as u64 > MAX => Line::TooLong,
        _ => Line::Data(line),
    })
}

pub fn serve(store: &MemoryStore, input: impl BufRead, mut output: impl Write) -> io::Result<()> {
    let mut input = input;
    loop {
        let line = match read_line(&mut input)? {
            Line::Eof => return Ok(()),
            Line::TooLong => {
                writeln!(
                    output,
                    "{}",
                    json!({"id":null,"ok":false,"error":"Zeile überschreitet 1 MiB; Verbindung beendet"})
                )?;
                output.flush()?;
                return Err(io::Error::other("JSONL-Zeile zu groß"));
            }
            Line::Data(line) => line,
        };
        let answer = match serde_json::from_slice::<Value>(&line) {
            Ok(value) => dispatch(store, value),
            Err(error) => json!({"id":null,"ok":false,"error":error.to_string()}),
        };
        writeln!(output, "{answer}")?;
        output.flush()?;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn proposals_are_not_recalled_until_external_validation() {
        let s = MemoryStore::in_memory().unwrap();
        let result = dispatch(
            &s,
            json!({"id":"first", "op":"propose", "scope":"demo", "kind":"long_term",
            "problem":"Transaktionen", "solution":"Atomar schreiben", "source":"unit-test"}),
        );
        assert_eq!(result["id"], "first");
        assert_eq!(result["data"]["status"], "pending");
        let recall = || {
            dispatch(
                &s,
                json!({"id":2,"op":"recall","scope":"demo","query":"Transaktionen"}),
            )
        };
        assert_eq!(recall()["data"]["memories"].as_array().unwrap().len(), 0);
        let id = result["data"]["memory_id"].as_i64().unwrap();
        s.validate(id, "Tester", "Integrationstest").unwrap();
        assert_eq!(recall()["data"]["memories"][0]["id"], id);
        assert_eq!(
            dispatch(&s, json!({"op":"validate","memory_id":id}))["ok"],
            false
        );
    }
    #[test]
    fn malformed_input_does_not_break_next_request() {
        let s = MemoryStore::in_memory().unwrap();
        let mut out = Vec::new();
        serve(
            &s,
            &b"kein json\n{\"id\":7,\"op\":\"stats\"}\n"[..],
            &mut out,
        )
        .unwrap();
        let text = String::from_utf8(out).unwrap();
        let lines: Vec<Value> = text
            .lines()
            .map(|s| serde_json::from_str(s).unwrap())
            .collect();
        assert_eq!(lines.len(), 2);
        assert_eq!(lines[0]["ok"], false);
        assert_eq!(lines[1]["id"], 7);
        assert_eq!(lines[1]["data"]["pending"], 0);
    }
    #[test]
    fn rejects_unknown_fields_and_oversize_lines() {
        let s = MemoryStore::in_memory().unwrap();
        assert_eq!(dispatch(&s, json!({"op":"stats","typo":true}))["ok"], false);
        let mut out = Vec::new();
        assert!(serve(&s, vec![b'x'; 1_048_577].as_slice(), &mut out).is_err());
        assert_eq!(String::from_utf8(out).unwrap().lines().count(), 1);
    }
}

#[cfg(test)]
mod project_tests {
    use super::*;
    #[test]
    fn project_and_chat_operations_roundtrip_with_explicit_scope() {
        let s = MemoryStore::in_memory().unwrap();
        let event = dispatch(
            &s,
            json!({"id":1,"op":"log","scope":"p","kind":"task","task_key":"schema",
            "task_status":"done","body":"Implementiert","source":"Testlauf"}),
        );
        assert_eq!(event["ok"], true);
        let conversation = dispatch(&s, json!({"op":"session_new","scope":"p","title":"Test"}));
        let id = conversation["data"]["conversation_id"].as_str().unwrap();
        assert_eq!(
            dispatch(
                &s,
                json!({"op":"message","conversation_id":id,"role":"assistant","content":"Fertig"})
            )["ok"],
            true
        );
        let resumed = dispatch(&s, json!({"op":"resume","scope":"p","conversation_id":id}));
        assert_eq!(resumed["data"]["tasks"][0]["task_status"], "done");
        assert_eq!(resumed["data"]["chat_tail"][0]["content"], "Fertig");
        assert_eq!(
            dispatch(
                &s,
                json!({"op":"resume","scope":"other","conversation_id":id})
            )["ok"],
            false
        );
        assert_eq!(
            dispatch(&s, json!({"op":"messages","conversation_id":id,"limit":10}))["data"]["messages"]
                [0]["content"],
            "Fertig"
        );
        assert_eq!(
            dispatch(&s, json!({"op":"journal","scope":"p","limit":10}))["data"]["events"][0]["kind"],
            "task"
        );
        assert_eq!(
            dispatch(&s, json!({"op":"sessions","scope":"p"}))["data"]["conversations"]
                .as_array()
                .unwrap()
                .len(),
            1
        );
    }
}
