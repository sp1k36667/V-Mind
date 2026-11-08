use serde_json::Value;
use std::{
    io::Write,
    process::{Command, Stdio},
};

struct Temp(std::path::PathBuf);
impl Temp {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "vmind-cli-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&path).unwrap();
        Self(path)
    }
}
impl Drop for Temp {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}
fn cli(args: &[&str]) -> Value {
    let out = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .arg("--json")
        .args(args)
        .output()
        .unwrap();
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    serde_json::from_slice(&out.stdout).unwrap()
}
#[test]
fn tools_propose_cli_reviews_and_withdraws_without_losing_history() {
    let temp = Temp::new();
    let path = temp.0.join("memory.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    let mut child = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(["serve", db])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    {
        let mut input = child.stdin.take().unwrap();
        writeln!(input,"{}",serde_json::json!({"id":"p","op":"propose","kind":"error_solution",
            "problem":"SQLite Migration","solution":"Atomar migrieren","source":"CLI-Test","scope":"projekt"})).unwrap();
        writeln!(
            input,
            "{}",
            serde_json::json!({"id":"r","op":"recall","query":"sqlite","scope":"projekt"})
        )
        .unwrap();
    }
    let out = child.wait_with_output().unwrap();
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let replies: Vec<Value> = String::from_utf8(out.stdout)
        .unwrap()
        .lines()
        .map(|s| serde_json::from_str(s).unwrap())
        .collect();
    assert_eq!(replies.len(), 2);
    assert_eq!(replies[0]["id"], "p");
    let id = replies[0]["data"]["memory_id"]
        .as_i64()
        .unwrap()
        .to_string();
    // Ungeprüft erscheint der Vorschlag nur als Hinweis.
    assert_eq!(replies[1]["data"]["memories"][0]["status"], "pending");
    assert!(
        cli(&[
            "--scope",
            "projekt",
            "recall",
            db,
            "SQLite",
            "--validated-only"
        ])
        .as_array()
        .unwrap()
        .is_empty()
    );
    let shown = cli(&["show", db, &id]);
    assert_eq!(shown["memory"]["status"], "pending");
    cli(&["validate", db, &id, "Testprüfer", "Workflow-Test"]);
    let found = cli(&[
        "--scope",
        "projekt",
        "recall",
        db,
        "Wie funktioniert die SQLITE Migration?",
    ]);
    assert_eq!(found[0]["source"], "CLI-Test");
    assert_eq!(found[0]["evidence"], "Workflow-Test");
    assert!(
        cli(&["recall", db, "SQLite"])
            .as_array()
            .unwrap()
            .is_empty()
    );
    cli(&[
        "invalidate",
        db,
        &id,
        "Testprüfer",
        "Korrektur erforderlich",
    ]);
    assert!(
        cli(&["--scope", "projekt", "recall", db, "SQLite"])
            .as_array()
            .unwrap()
            .is_empty()
    );
    let shown = cli(&["show", db, &id]);
    assert_eq!(shown["memory"]["status"], "invalidated");
    assert_eq!(shown["history"].as_array().unwrap().len(), 3);
}
#[test]
fn typo_in_database_path_does_not_create_an_empty_database() {
    let temp = Temp::new();
    let path = temp.0.join("typo.db");
    let out = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(["recall", path.to_str().unwrap(), "sqlite"])
        .output()
        .unwrap();
    assert!(!out.status.success());
    assert!(!path.exists());
}

fn model_server(body: &'static str) -> (String, std::thread::JoinHandle<Value>) {
    use std::{io::Read, net::TcpListener, time::Duration};
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let endpoint = format!("http://{}", listener.local_addr().unwrap());
    let worker = std::thread::spawn(move || {
        let (mut socket, _) = listener.accept().unwrap();
        socket
            .set_read_timeout(Some(Duration::from_secs(5)))
            .unwrap();
        let mut bytes = Vec::new();
        let mut buf = [0; 4096];
        loop {
            let n = socket.read(&mut buf).unwrap();
            assert!(n > 0);
            bytes.extend_from_slice(&buf[..n]);
            if let Some(pos) = bytes.windows(4).position(|w| w == b"\r\n\r\n") {
                let headers = String::from_utf8_lossy(&bytes[..pos]);
                let len: usize = headers
                    .lines()
                    .find_map(|line| {
                        let (k, v) = line.split_once(':')?;
                        k.eq_ignore_ascii_case("content-length")
                            .then(|| v.trim().parse().unwrap())
                    })
                    .unwrap();
                if bytes.len() >= pos + 4 + len {
                    let value = serde_json::from_slice(&bytes[pos + 4..pos + 4 + len]).unwrap();
                    write!(socket,"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",body.len()).unwrap();
                    return value;
                }
            }
        }
    });
    (endpoint, worker)
}
#[test]
fn separate_cli_processes_reload_last_answer_and_project_tasks() {
    let temp = Temp::new();
    let path = temp.0.join("context.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    cli(&[
        "--scope",
        "projekt",
        "task",
        db,
        "migration",
        "done",
        "Migration implementiert und getestet",
        "CLI-Test",
    ]);
    for (question, response) in [
        (
            "Was ist erledigt?",
            r#"{"response":"Migration fertig.","done":true}"#,
        ),
        (
            "Was hattest du zuletzt gesagt?",
            r#"{"response":"Ich sagte: Migration fertig.","done":true}"#,
        ),
    ] {
        let (endpoint, worker) = model_server(response);
        let out = Command::new(env!("CARGO_BIN_EXE_vmind"))
            .env("VMIND_OLLAMA_URL", endpoint)
            .args(["--json", "--scope", "projekt", "ask", db, question])
            .output()
            .unwrap();
        assert!(
            out.status.success(),
            "{}",
            String::from_utf8_lossy(&out.stderr)
        );
        let sent = worker.join().unwrap();
        let prompt: Value = serde_json::from_str(sent["prompt"].as_str().unwrap()).unwrap();
        assert_eq!(prompt["project_context"]["tasks"][0]["task_status"], "done");
        if question.starts_with("Was hattest") {
            assert_eq!(
                prompt["project_context"]["recent_messages_newest_first"][0]["content"],
                "Migration fertig."
            );
        }
    }
    let resume = cli(&["--scope", "projekt", "resume", db]);
    assert_eq!(resume["message_count"], 4);
    assert_eq!(
        resume["chat_tail"][3]["content"],
        "Ich sagte: Migration fertig."
    );
}
#[test]
fn failed_model_call_keeps_user_message_without_fabricating_an_answer() {
    let temp = Temp::new();
    let path = temp.0.join("failed.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    let (endpoint, worker) = model_server(r#"{"response":"","done":true}"#);
    let out = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .env("VMIND_OLLAMA_URL", endpoint)
        .args(["--scope", "projekt", "ask", db, "Eine Frage"])
        .output()
        .unwrap();
    assert!(!out.status.success());
    worker.join().unwrap();
    let resume = cli(&["--scope", "projekt", "resume", db]);
    let messages = resume["chat_tail"].as_array().unwrap();
    assert_eq!(messages[0]["role"], "user");
    assert_eq!(messages[0]["content"], "Eine Frage");
    assert_eq!(messages[1]["role"], "tool");
    assert!(!messages.iter().any(|m| m["role"] == "assistant"));
}
#[test]
fn mcp_server_handshakes_and_writes_journal_in_configured_scope() {
    let temp = Temp::new();
    let path = temp.0.join("mcp.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    let mut child = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(["--scope", "projekt", "mcp", db])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    {
        let mut input = child.stdin.take().unwrap();
        for message in [
            serde_json::json!({"jsonrpc":"2.0","id":1,"method":"initialize","params":{
                "protocolVersion":"2025-06-18","capabilities":{},
                "clientInfo":{"name":"test","version":"1"}}}),
            serde_json::json!({"jsonrpc":"2.0","method":"notifications/initialized"}),
            serde_json::json!({"jsonrpc":"2.0","id":2,"method":"tools/list"}),
            serde_json::json!({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{
                "name":"log","arguments":{"kind":"task","task_key":"mcp",
                "task_status":"done","body":"MCP getestet","source":"Workflow-Test"}}}),
        ] {
            writeln!(input, "{message}").unwrap();
        }
    }
    let out = child.wait_with_output().unwrap();
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let replies: Vec<Value> = String::from_utf8(out.stdout)
        .unwrap()
        .lines()
        .map(|s| serde_json::from_str(s).unwrap())
        .collect();
    assert_eq!(replies.len(), 3);
    assert_eq!(replies[0]["result"]["protocolVersion"], "2025-06-18");
    assert!(replies[1]["result"]["tools"].as_array().unwrap().len() >= 10);
    assert_eq!(replies[2]["result"]["isError"], false);
    let resume = cli(&["--scope", "projekt", "resume", db]);
    assert_eq!(resume["tasks"][0]["task_key"], "mcp");
    assert_eq!(resume["tasks"][0]["task_status"], "done");
}
fn cli_status(args: &[&str]) -> (bool, Value) {
    let out = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .arg("--json")
        .args(args)
        .output()
        .unwrap();
    let value = serde_json::from_slice(&out.stdout).unwrap_or(Value::Null);
    (out.status.success(), value)
}
#[test]
fn check_commands_drive_the_learning_loop_end_to_end() {
    let temp = Temp::new();
    let path = temp.0.join("checks.db");
    let db = path.to_str().unwrap();
    let workdir = temp.0.join("projekt");
    std::fs::create_dir(&workdir).unwrap();
    let dir = workdir.to_str().unwrap();
    cli(&["init", db]);
    let added = cli(&[
        "--scope",
        "p",
        "add",
        db,
        "error_solution",
        "Markerdatei fehlt",
        "Markerdatei anlegen",
        "Workflow-Test",
    ]);
    let id = added["id"].as_i64().unwrap().to_string();
    cli(&[
        "check-set",
        db,
        &id,
        "Testleiter",
        dir,
        "sh",
        "-c",
        "test -f marker",
    ]);

    let (passed, failed) = cli_status(&["check", db, &id]);
    assert!(!passed);
    assert_eq!(failed["applied"]["status_after"], "pending");

    std::fs::write(workdir.join("marker"), "").unwrap();
    let ok = cli(&["check", db, &id]);
    assert_eq!(ok["applied"]["status_before"], "pending");
    assert_eq!(ok["applied"]["status_after"], "validated");
    let found = cli(&["--scope", "p", "recall", db, "Markerdatei"]);
    assert_eq!(found[0]["validated_by"], "vmind check");
    assert_eq!(found[0]["check"]["state"], "passed");
    let shown = cli(&["show", db, &id]);
    assert_eq!(shown["check"]["argv"][2], "test -f marker");
    assert_eq!(shown["check_runs"].as_array().unwrap().len(), 2);

    assert!(cli(&["--scope", "p", "revalidate", db])["failed"] == 0);
    std::fs::remove_file(workdir.join("marker")).unwrap();
    let (passed, report) = cli_status(&["--scope", "p", "revalidate", db]);
    assert!(!passed);
    assert_eq!(report["results"][0]["status_after"], "validated");
    let retrieved = cli(&["--scope", "p", "recall", db, "Markerdatei"]);
    assert_eq!(retrieved[0]["check"]["state"], "failed");
    assert_eq!(retrieved[0]["status"], "validated");
    let project = cli(&["--scope", "p", "report", db]);
    assert_eq!(project["knowledge"][0]["check"]["state"], "failed");
    let human = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(["--scope", "p", "recall", db, "Markerdatei"])
        .output()
        .unwrap();
    assert!(human.status.success());
    assert!(String::from_utf8(human.stdout).unwrap().contains("WARNUNG"));

    let (passed, report) = cli_status(&["--scope", "p", "revalidate", db, "--invalidate"]);
    assert!(!passed);
    assert_eq!(report["results"][0]["status_after"], "invalidated");
    assert_eq!(
        cli(&["--scope", "p", "revalidate", db])["results"],
        serde_json::json!([])
    );
}
#[test]
fn check_set_rejects_missing_directory_and_unknown_entry() {
    let temp = Temp::new();
    let path = temp.0.join("reject.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    let missing = temp.0.join("fehlt");
    let (ok, _) = cli_status(&["check-set", db, "1", "T", missing.to_str().unwrap(), "true"]);
    assert!(!ok);
    let (ok, _) = cli_status(&["check-set", db, "1", "T", temp.0.to_str().unwrap(), "true"]);
    assert!(!ok);
}

#[cfg(unix)]
#[test]
fn output_timeout_never_validates_an_entry() {
    let temp = Temp::new();
    let path = temp.0.join("output-timeout.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    let added = cli(&[
        "add",
        db,
        "error_solution",
        "Prüfung hängt",
        "Zeitlimit anwenden",
        "Regressionstest",
    ]);
    let id = added["id"].as_i64().unwrap().to_string();
    cli(&[
        "check-set",
        db,
        &id,
        "Test",
        temp.0.to_str().unwrap(),
        "sh",
        "-c",
        "sleep 3 & echo parent-done",
    ]);
    let started = std::time::Instant::now();
    let output = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .env("VMIND_CHECK_TIMEOUT", "1")
        .args(["--json", "check", db, &id])
        .output()
        .unwrap();
    assert!(!output.status.success());
    assert!(started.elapsed() < std::time::Duration::from_millis(2500));
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["applied"]["outcome"], "error");
    assert_eq!(report["applied"]["status_after"], "pending");
    let stored = cli(&["show", db, &id]);
    assert_eq!(stored["memory"]["status"], "pending");
    assert_eq!(stored["check_runs"][0]["outcome"], "error");
}

#[test]
fn backup_and_doctor_preserve_restorable_state_without_overwriting() {
    let temp = Temp::new();
    let source = temp.0.join("source.db");
    let copy = temp.0.join("copy.db");
    let db = source.to_str().unwrap();
    let target = copy.to_str().unwrap();
    cli(&["init", db]);
    cli(&[
        "--scope",
        "project",
        "task",
        db,
        "next",
        "open",
        "Fortsetzen",
        "Test",
    ]);
    assert_eq!(cli(&["doctor", db])["healthy"], true);
    let report = cli(&["backup", db, target]);
    assert_eq!(report["verified"], true);
    assert_eq!(
        cli(&["--scope", "project", "resume", target])["tasks"][0]["task_key"],
        "next"
    );
    let saved = std::fs::read(&copy).unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(["backup", db, target])
        .output()
        .unwrap();
    assert!(!output.status.success());
    assert_eq!(std::fs::read(copy).unwrap(), saved);
    let missing = temp.0.join("missing.db");
    assert!(
        !Command::new(env!("CARGO_BIN_EXE_vmind"))
            .args(["doctor", missing.to_str().unwrap()])
            .output()
            .unwrap()
            .status
            .success()
    );
    assert!(!missing.exists());
}

#[test]
fn independent_processes_preserve_every_concurrent_journal_write() {
    let temp = Temp::new();
    let path = temp.0.join("parallel.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    let mut children = Vec::new();
    for index in 0..16 {
        children.push(
            Command::new(env!("CARGO_BIN_EXE_vmind"))
                .args([
                    "--json",
                    "--scope",
                    "parallel",
                    "log",
                    db,
                    "note",
                    &format!("writer-{index}"),
                    "process-test",
                ])
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .spawn()
                .unwrap(),
        );
    }
    for child in children {
        let output = child.wait_with_output().unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
    let events = cli(&["--scope", "parallel", "journal", db]);
    let rows = events.as_array().unwrap();
    assert_eq!(rows.len(), 16);
    let bodies = rows
        .iter()
        .map(|e| e["body"].as_str().unwrap())
        .collect::<std::collections::HashSet<_>>();
    assert_eq!(bodies.len(), 16);
    assert_eq!(cli(&["doctor", db])["healthy"], true);
}

#[test]
fn report_prints_markdown_and_leaves_the_database_unchanged() {
    let temp = Temp::new();
    let path = temp.0.join("report.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    cli(&[
        "--scope",
        "p",
        "task",
        db,
        "docs",
        "blocked",
        "Doku fehlt",
        "Test",
    ]);
    let before = std::fs::read(&path).unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(["--scope", "p", "report", db])
        .output()
        .unwrap();
    assert!(output.status.success());
    let text = String::from_utf8(output.stdout).unwrap();
    assert!(text.starts_with("# Projektbericht: p"));
    assert!(text.contains("- **blocked** docs: Doku fehlt"));
    assert_eq!(
        cli(&["--scope", "p", "report", db])["stats"]["schema_version"],
        6
    );
    assert_eq!(std::fs::read(&path).unwrap(), before);
}

#[test]
fn audit_secrets_reports_kind_and_place_but_never_the_value() {
    let temp = Temp::new();
    let path = temp.0.join("audit.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    // Zur Laufzeit zusammengesetzt; kein echtes Geheimnis.
    let token = format!("gh{}_{}", "p", "a1B2".repeat(9));
    let id = cli(&[
        "--scope",
        "p",
        "add",
        db,
        "error_solution",
        "Push schlägt fehl",
        &format!("Mit {token} anmelden"),
        "Test",
    ])["id"]
        .as_i64()
        .unwrap();
    let before = std::fs::read(&path).unwrap();

    let report = cli(&["audit-secrets", db]);
    let human = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(["audit-secrets", db])
        .output()
        .unwrap();

    assert!(human.status.success(), "Funde sind kein Fehler");
    let text = String::from_utf8(human.stdout).unwrap();
    assert!(text.contains(&format!("memories #{id} Feld solution: GitHub-Token")));
    assert!(text.contains("kein Fund heißt nicht geheimnisfrei"));
    assert_eq!(report["findings"][0]["kind"], "github_token");
    assert_eq!(report["findings"][0]["memory_id"], id);
    for output in [report.to_string(), text] {
        assert!(!output.contains(&token[..12]), "Fundtext ausgegeben");
    }
    assert!(human.stderr.is_empty());
    assert_eq!(std::fs::read(&path).unwrap(), before);

    let missing = temp.0.join("fehlt.db");
    let out = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(["audit-secrets", missing.to_str().unwrap()])
        .output()
        .unwrap();
    assert!(!out.status.success());
    assert!(!missing.exists(), "fehlende Datenbank angelegt");
    // Auch Fehler dürfen keine potenziell vertraulichen Dateinamen wiederholen.
    let private_path = temp.0.join(format!("{token}.db"));
    let failed = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(["audit-secrets", private_path.to_str().unwrap()])
        .output()
        .unwrap();
    assert!(!failed.status.success());
    assert!(!String::from_utf8_lossy(&failed.stdout).contains(&token));
    assert!(!String::from_utf8_lossy(&failed.stderr).contains(&token));
}

fn observe(db: &str, input: &str) -> std::process::Output {
    use std::io::Write;
    let mut child = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .env("CLAUDE_PROJECT_DIR", "/projekt")
        .args(["--scope", "p", "observe", db])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(input.as_bytes())
        .unwrap();
    child.wait_with_output().unwrap()
}

#[test]
fn observe_hook_stores_tool_and_path_but_never_content_command_or_error() {
    let temp = Temp::new();
    let path = temp.0.join("observe.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    let write = r#"{"session_id":"s1","tool_use_id":"toolu_w","hook_event_name":"PostToolUse",
        "tool_name":"Write","cwd":"/projekt",
        "tool_input":{"file_path":"/projekt/src/neu.rs","content":"GEHEIMER-INHALT"},
        "tool_response":{"filePath":"/projekt/src/neu.rs","type":"create"}}"#;
    let failure = r#"{"session_id":"s1","tool_use_id":"toolu_b","hook_event_name":"PostToolUseFailure",
        "tool_name":"Bash","cwd":"/projekt","tool_input":{"command":"echo GEHEIMES-KOMMANDO"},
        "error":"Exit code 1\nGEHEIMER-FEHLER","is_interrupt":false}"#;
    for input in [write, failure, write] {
        let out = observe(db, input);
        assert!(
            out.status.success(),
            "{}",
            String::from_utf8_lossy(&out.stderr)
        );
        assert!(out.stdout.is_empty());
    }
    let resume = cli(&["--scope", "p", "resume", db]);
    assert_eq!(resume["observation_count"], 2);
    let session = &resume["observed_sessions"][0];
    assert_eq!(session["calls"], 2);
    assert_eq!(session["failed"], 1);
    assert_eq!(session["paths"][0], "src/neu.rs");
    let bytes = String::from_utf8_lossy(&std::fs::read(&path).unwrap()).into_owned();
    for secret in ["GEHEIMER-INHALT", "GEHEIMES-KOMMANDO", "GEHEIMER-FEHLER"] {
        assert!(!bytes.contains(secret), "{secret} gespeichert");
    }
    let missing = temp.0.join("fehlt.db");
    assert!(!observe(missing.to_str().unwrap(), write).status.success());
    assert!(!missing.exists());
}

#[test]
fn validation_errors_are_shown_without_sqlite_jargon() {
    let temp = Temp::new();
    let path = temp.0.join("fehler.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    let output = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(["--scope", "p", "log", db, "note", " ", "Quelle"])
        .output()
        .unwrap();
    assert!(!output.status.success());
    let message = String::from_utf8_lossy(&output.stderr);
    assert!(message.starts_with("V-Mind: "), "{message}");
    assert!(!message.contains("Invalid parameter name"), "{message}");
}

#[test]
fn start_prompt_defaults_to_german_and_offers_english() {
    let default = cli(&["start-prompt"]);
    assert_eq!(default["language"], "de");
    assert!(
        default["prompt"]
            .as_str()
            .unwrap()
            .contains("Startanweisung")
    );
    let english = cli(&["start-prompt", "en"]);
    assert_eq!(english["language"], "en");
    assert!(
        english["prompt"]
            .as_str()
            .unwrap()
            .contains("start instructions")
    );
    let (ok, _) = cli_status(&["start-prompt", "fr"]);
    assert!(!ok);
}

#[test]
fn recall_limit_option_returns_more_than_five_and_rejects_invalid_values() {
    let temp = Temp::new();
    let path = temp.0.join("limit.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    for n in 0..7 {
        let problem = format!("Gerüstname {n} umbenannt");
        let added = cli(&[
            "add",
            db,
            "error_solution",
            &problem,
            "Namen übernehmen",
            "Test",
        ]);
        let id = added["id"].to_string();
        cli(&["validate", db, &id, "Testprüfer", "Limit-Test"]);
    }
    let count = |args: &[&str]| cli(args).as_array().unwrap().len();
    assert_eq!(count(&["recall", db, "Gerüstname umbenannt"]), 5);
    assert_eq!(
        count(&["recall", db, "Gerüstname umbenannt", "--limit", "7"]),
        7
    );
    assert_eq!(
        count(&["recall", db, "Gerüstname umbenannt", "--limit", "2"]),
        2
    );
    for bad in ["0", "21", "fünf", "-1"] {
        let (ok, _) = cli_status(&["recall", db, "Gerüstname", "--limit", bad]);
        assert!(!ok, "--limit {bad} angenommen");
    }
}

#[test]
fn invalid_recall_limit_is_rejected_before_the_database_is_opened() {
    let temp = Temp::new();
    let path = temp.0.join("keine-datenbank.db");
    std::fs::write(&path, b"kein SQLite").unwrap();
    for bad in ["0", "21", "fünf"] {
        let out = Command::new(env!("CARGO_BIN_EXE_vmind"))
            .args(["recall", path.to_str().unwrap(), "x", "--limit", bad])
            .output()
            .unwrap();
        assert!(!out.status.success(), "--limit {bad} angenommen");
        let message = String::from_utf8_lossy(&out.stderr);
        assert!(message.contains("Limit muss 1 bis 20 sein"), "{message}");
    }
    assert_eq!(std::fs::read(&path).unwrap(), b"kein SQLite");
}

#[test]
fn journal_mode_command_switches_explicitly_and_doctor_reports_it() {
    let temp = Temp::new();
    let path = temp.0.join("modus.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    assert_eq!(cli(&["doctor", db])["journal_mode"], "delete");
    let wechsel = cli(&["journal-mode", db, "wal"]);
    assert_eq!(wechsel["previous"], "delete");
    assert_eq!(wechsel["current"], "wal");
    assert_eq!(wechsel["changed"], true);
    assert!(std::path::Path::new(wechsel["backup"].as_str().unwrap()).exists());
    assert_eq!(cli(&["doctor", db])["journal_mode"], "wal");
    let gleich = cli(&["journal-mode", db, "wal"]);
    assert_eq!(gleich["changed"], false);
    assert!(gleich["backup"].is_null());
    let (ok, _) = cli_status(&["journal-mode", db, "truncate"]);
    assert!(!ok);
    assert_eq!(cli(&["journal-mode", db, "delete"])["current"], "delete");
}
#[test]
fn real_check_repair_becomes_one_pending_proposal_end_to_end() {
    let temp = Temp::new();
    let path = temp.0.join("repair.db");
    let db = path.to_str().unwrap();
    let workdir = temp.0.join("projekt");
    std::fs::create_dir(&workdir).unwrap();
    cli(&["init", db]);
    let id = cli(&[
        "--scope",
        "p",
        "add",
        db,
        "error_solution",
        "Marker fehlt",
        "Marker anlegen",
        "Test",
    ])["id"]
        .as_i64()
        .unwrap()
        .to_string();
    let dir = workdir.to_str().unwrap();
    cli(&["check-set", db, &id, "T", dir, "sh", "-c", "test -f marker"]);
    std::fs::write(workdir.join("marker"), "").unwrap();
    cli(&["check", db, &id]);
    std::fs::remove_file(workdir.join("marker")).unwrap();
    assert!(!cli_status(&["check", db, &id]).0);
    assert_eq!(cli(&["--scope", "p", "repairs", db]), serde_json::json!([]));
    std::fs::write(workdir.join("marker"), "").unwrap();
    cli(&["check", db, &id]);

    let repairs = cli(&["--scope", "p", "repairs", db]);
    assert_eq!(repairs.as_array().unwrap().len(), 1);
    assert!(
        !repairs.to_string().contains("marker"),
        "keine Befehle oder Ausgaben"
    );
    let run = repairs[0]["failed_run"].as_i64().unwrap().to_string();
    let resumed = cli(&["--scope", "p", "resume", db]);
    assert_eq!(resumed["open_repairs"]["total"], 1);
    assert_eq!(
        resumed["open_repairs"]["newest_failed_runs"][0],
        repairs[0]["failed_run"]
    );
    let human = |scope: &str| {
        let out = Command::new(env!("CARGO_BIN_EXE_vmind"))
            .args(["--scope", scope, "resume", db])
            .output()
            .unwrap();
        assert!(out.status.success());
        String::from_utf8(out.stdout).unwrap()
    };
    assert!(human("p").contains(&format!(
        "Reparaturen ohne Vorschlag: 1 (neueste Läufe: {run})"
    )));
    assert!(
        !human("x").contains("Reparaturen"),
        "fremder Bereich sieht nichts"
    );
    let (ok, _) = cli_status(&["--scope", "x", "propose-repair", db, &run, "P", "L"]);
    assert!(!ok, "fremder Bereich");
    let proposed = cli(&[
        "--scope",
        "p",
        "propose-repair",
        db,
        &run,
        "Marker gelöscht",
        "Marker neu anlegen",
    ]);
    assert_eq!(proposed["status"], "pending");
    assert_eq!(
        cli(&["--scope", "p", "resume", db])["open_repairs"]["total"],
        0
    );
    assert!(!human("p").contains("Reparaturen ohne Vorschlag"));
    let (ok, _) = cli_status(&["--scope", "p", "propose-repair", db, &run, "P", "L"]);
    assert!(!ok, "doppelt");
    let pending = cli(&["--scope", "p", "pending", db]);
    assert_eq!(pending.as_array().unwrap().len(), 1);
    assert!(
        pending[0]["source"]
            .as_str()
            .unwrap()
            .starts_with("Reparatur: Prüfbefehl #")
    );
}
#[test]
fn passing_check_right_after_failure_names_the_repair_once() {
    let temp = Temp::new();
    let path = temp.0.join("hint.db");
    let db = path.to_str().unwrap();
    let workdir = temp.0.join("projekt");
    std::fs::create_dir(&workdir).unwrap();
    let marker = workdir.join("marker");
    cli(&["init", db]);
    let added = cli(&["--scope", "p", "add", db, "error_solution", "M", "L", "T"]);
    let id = added["id"].as_i64().unwrap().to_string();
    let dir = workdir.to_str().unwrap();
    cli(&["check-set", db, &id, "T", dir, "sh", "-c", "test -f marker"]);
    std::fs::write(&marker, "").unwrap();
    assert_eq!(
        cli(&["--scope", "p", "check", db, &id])["repair"],
        Value::Null
    );
    std::fs::remove_file(&marker).unwrap();
    assert!(!cli_status(&["--scope", "p", "check", db, &id]).0);
    std::fs::write(&marker, "").unwrap();

    let out = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(["--scope", "p", "check", db, &id])
        .output()
        .unwrap();
    assert!(out.status.success(), "Hinweis ändert das Ergebnis nicht");
    let text = String::from_utf8(out.stdout).unwrap();
    let failed_run = cli(&["--scope", "p", "repairs", db])[0]["failed_run"].clone();
    assert!(text.contains(&format!("propose-repair DB {failed_run} PROBLEM LÖSUNG")));
    let hint = text
        .lines()
        .find(|l| l.starts_with("Reparatur erkannt"))
        .unwrap();
    assert!(!hint.contains("marker"), "kein Befehl im Hinweis");

    let again = cli(&["--scope", "p", "check", db, &id]);
    assert_eq!(
        again["repair"],
        Value::Null,
        "nur der gerade abschließende Lauf"
    );
    std::fs::remove_file(&marker).unwrap();
    assert!(!cli_status(&["--scope", "p", "revalidate", db]).0);
    std::fs::write(&marker, "").unwrap();
    let report = cli(&["--scope", "p", "revalidate", db]);
    assert_eq!(report["repairs"].as_array().unwrap().len(), 1);
    let run = report["repairs"][0]["failed_run"]
        .as_i64()
        .unwrap()
        .to_string();
    cli(&[
        "--scope",
        "p",
        "propose-repair",
        db,
        &run,
        "Marker weg",
        "Neu anlegen",
    ]);
    std::fs::remove_file(&marker).unwrap();
    assert!(!cli_status(&["--scope", "p", "check", db, &id]).0);
    std::fs::write(&marker, "").unwrap();
    let foreign = cli(&["--scope", "x", "check", db, &id]);
    assert_eq!(foreign["repair"], Value::Null, "fremder Bereich");
}
#[test]
fn recall_marks_unconfirmed_hints_and_validated_only_hides_them() {
    let temp = Temp::new();
    let path = temp.0.join("hints.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    let ok = cli(&[
        "--scope",
        "p",
        "add",
        db,
        "error_solution",
        "Proxy blockiert",
        "Bestätigt",
        "T",
    ]);
    let ok_id = ok["id"].as_i64().unwrap().to_string();
    cli(&["validate", db, &ok_id, "Prüfer", "Test"]);
    cli(&[
        "--scope",
        "p",
        "add",
        db,
        "error_solution",
        "Proxy langsam",
        "Vermutung",
        "T",
    ]);
    let found = cli(&["--scope", "p", "recall", db, "Proxy"]);
    assert_eq!(found[0]["status"], "validated");
    assert_eq!(found[1]["status"], "pending");
    let strict = cli(&["--scope", "p", "recall", db, "Proxy", "--validated-only"]);
    assert_eq!(strict.as_array().unwrap().len(), 1);
    let limited = cli(&[
        "--scope",
        "p",
        "recall",
        db,
        "Proxy",
        "--limit",
        "1",
        "--validated-only",
    ]);
    assert_eq!(limited.as_array().unwrap().len(), 1);
    let out = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(["--scope", "p", "recall", db, "Proxy"])
        .output()
        .unwrap();
    let text = String::from_utf8(out.stdout).unwrap();
    let mark = text.find("UNGEPRÜFT").unwrap();
    assert!(
        mark > text.find("Bestätigt").unwrap(),
        "Hinweis steht hinter dem bestätigten Eintrag"
    );
    assert_eq!(text.matches("UNGEPRÜFT").count(), 1);
}
#[test]
fn validated_only_is_read_only_as_an_option_behind_db_and_query() {
    let temp = Temp::new();
    let dir = temp.0.join("--validated-only");
    std::fs::create_dir(&dir).unwrap();
    // Datenbank, deren Pfad wörtlich mit der Option endet.
    let path = dir.join("--validated-only");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    cli(&[
        "--scope",
        "p",
        "add",
        db,
        "error_solution",
        "--validated-only Hinweis",
        "L",
        "T",
    ]);
    // Suchtext gleich der Option: bleibt Suchtext, Hinweis erscheint.
    let as_query = cli(&["--scope", "p", "recall", db, "--validated-only"]);
    assert_eq!(as_query[0]["status"], "pending");
    // Als Option hinter dem Suchtext: blendet den Hinweis aus.
    let strict = cli(&[
        "--scope",
        "p",
        "recall",
        db,
        "--validated-only",
        "--validated-only",
    ]);
    assert_eq!(strict, serde_json::json!([]));
    // Wert nach --limit wird nicht als Schalter verbraucht.
    let (ok, _) = cli_status(&[
        "--scope",
        "p",
        "recall",
        db,
        "Hinweis",
        "--limit",
        "--validated-only",
    ]);
    assert!(!ok, "ungültiges Limit statt stillem Schalter");
    let strict_limit = cli(&[
        "--scope",
        "p",
        "recall",
        db,
        "Hinweis",
        "--validated-only",
        "--limit",
        "2",
    ]);
    assert_eq!(strict_limit, serde_json::json!([]));
}
fn hint(db: &str, scope: &str, input: &str) -> (bool, String) {
    use std::io::Write;
    let mut child = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(["--scope", scope, "hint", db])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    // Ein Hook darf auch bei vorzeitig geschlossener Eingabe nicht scheitern.
    let _ = child.stdin.take().unwrap().write_all(input.as_bytes());
    let out = child.wait_with_output().unwrap();
    (out.status.success(), String::from_utf8(out.stdout).unwrap())
}
fn failure(error: &str) -> String {
    serde_json::json!({"session_id":"s1","tool_use_id":"toolu_f","hook_event_name":"PostToolUseFailure",
        "tool_name":"Bash","cwd":"/projekt","tool_input":{"command":"echo GEHEIMES-KOMMANDO"},
        "error":error,"is_interrupt":false})
    .to_string()
}
#[test]
fn hint_hook_returns_matching_knowledge_as_marked_context_without_writing() {
    let temp = Temp::new();
    let path = temp.0.join("hint.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    let ok = cli(&[
        "--scope",
        "p",
        "add",
        db,
        "error_solution",
        "database is locked beim Schreiben",
        "Wiederholen außerhalb von Transaktionen",
        "PR 42",
    ]);
    cli(&[
        "validate",
        db,
        &ok["id"].as_i64().unwrap().to_string(),
        "Prüfer",
        "Test",
    ]);
    cli(&[
        "--scope",
        "p",
        "add",
        db,
        "error_solution",
        "database is locked auf NTFS",
        "Journalmodus delete",
        "PR 51",
    ]);
    let fremd = cli(&[
        "--scope",
        "anderes",
        "add",
        db,
        "error_solution",
        "database is locked fremd",
        "FREMDE-LÖSUNG",
        "T",
    ]);
    cli(&[
        "validate",
        db,
        &fremd["id"].as_i64().unwrap().to_string(),
        "Prüfer",
        "Test",
    ]);
    let zurueck = cli(&[
        "--scope",
        "p",
        "add",
        db,
        "error_solution",
        "database is locked alt",
        "ZURÜCKGEZOGENE-LÖSUNG",
        "T",
    ]);
    cli(&[
        "invalidate",
        db,
        &zurueck["id"].as_i64().unwrap().to_string(),
        "Prüfer",
        "falsch",
    ]);
    let before = std::fs::read(&path).unwrap();

    let (ok, out) = hint(
        db,
        "p",
        &failure("Error: database is locked GEHEIMER-FEHLER"),
    );
    assert!(ok);
    let answer: Value = serde_json::from_str(&out).unwrap();
    assert_eq!(
        answer["hookSpecificOutput"]["hookEventName"],
        "PostToolUseFailure"
    );
    let context = answer["hookSpecificOutput"]["additionalContext"]
        .as_str()
        .unwrap();
    assert!(context.contains("Wiederholen außerhalb von Transaktionen"));
    assert!(context.contains("[geprüft]") && context.contains("[UNGEPRÜFT]"));
    assert!(context.find("[geprüft]").unwrap() < context.find("[UNGEPRÜFT]").unwrap());
    assert!(context.contains("keine Anweisungen"));
    for absent in [
        "FREMDE-LÖSUNG",
        "ZURÜCKGEZOGENE-LÖSUNG",
        "GEHEIMER-FEHLER",
        "GEHEIMES-KOMMANDO",
    ] {
        assert!(!context.contains(absent), "{absent} im Kontext");
    }
    assert_eq!(
        std::fs::read(&path).unwrap(),
        before,
        "Datenbank unverändert"
    );
}
#[test]
fn hint_hook_stays_silent_and_successful_on_every_failure_path() {
    let temp = Temp::new();
    let path = temp.0.join("still.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    let quiet = |db: &str, input: &str| {
        let (ok, out) = hint(db, "p", input);
        assert!(ok, "Hook muss erfolgreich enden: {input}");
        assert!(out.is_empty(), "keine Ausgabe erwartet bei {input}: {out}");
    };
    quiet(db, &failure("völlig unbekannter Fehler ohne Treffer"));
    quiet(db, "");
    quiet(db, "kein json");
    quiet(
        db,
        r#"{"hook_event_name":"PostToolUse","tool_name":"Bash","error":"database"}"#,
    );
    quiet(
        db,
        r#"{"hook_event_name":"PostToolUseFailure","tool_name":"Bash"}"#,
    );
    let missing = temp.0.join("fehlt.db");
    quiet(missing.to_str().unwrap(), &failure("database is locked"));
    assert!(!missing.exists(), "Hook legt keine Datenbank an");
}
#[test]
fn resume_reports_open_hints_and_stale_fields_in_json_and_text() {
    let temp = Temp::new();
    let path = temp.0.join("stand.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    cli(&[
        "--scope",
        "p",
        "add",
        db,
        "long_term",
        "Vermutung A",
        "L",
        "T",
    ]);
    cli(&[
        "--scope",
        "p",
        "add",
        db,
        "long_term",
        "Vermutung B",
        "L",
        "T",
    ]);
    cli(&[
        "--scope",
        "p",
        "task",
        db,
        "k",
        "in_progress",
        "frische Aufgabe",
        "T",
    ]);
    let json = cli(&["--scope", "p", "resume", db]);
    assert_eq!(json["open_hints"]["total"], 2);
    assert_eq!(json["open_hints"]["newest_ids"], serde_json::json!([2, 1]));
    assert_eq!(
        json["stale_tasks"],
        serde_json::json!([]),
        "heute angelegt ist nicht veraltet"
    );
    let out = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(["--scope", "p", "resume", db])
        .output()
        .unwrap();
    let text = String::from_utf8(out.stdout).unwrap();
    assert!(text.contains("Ungeprüfte Einträge in diesem Bereich: 2 (neueste: #2, #1)"));
    assert!(!text.contains("möglicherweise veraltet"));
}

#[test]
fn journal_search_lists_matches_of_the_exact_scope_as_json_and_text() {
    let temp = Temp::new();
    let path = temp.0.join("tagebuch.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    let log = |scope: &str, body: &str| {
        cli(&["--scope", scope, "log", db, "note", body, "Test"])["event_id"]
            .as_i64()
            .unwrap()
    };
    let old = log("p", "Migration geprüft");
    log("global", "Migration global");
    log("anderes", "Migration anderswo");
    cli(&[
        "--scope",
        "p",
        "task",
        db,
        "suche",
        "done",
        "Migration abgeschlossen",
        "cargo test",
    ]);
    let found = cli(&["--scope", "p", "journal-search", db, "MIGRATION"]);
    let found = found.as_array().unwrap();
    assert_eq!(found.len(), 2);
    assert!(found.iter().all(|e| e["scope"] == "p"));
    assert_eq!(found[0]["task_key"], "suche");
    assert_eq!(found[1]["id"], old);
    let limited = cli(&[
        "--scope",
        "p",
        "journal-search",
        db,
        "migration",
        "--limit",
        "1",
    ]);
    assert_eq!(limited.as_array().unwrap().len(), 1);
    let out = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(["--scope", "p", "journal-search", db, "migration"])
        .output()
        .unwrap();
    assert!(out.status.success());
    let text = String::from_utf8(out.stdout).unwrap();
    assert!(text.contains("task / suche: done]"), "{text}");
    assert!(
        text.contains("Migration abgeschlossen\nQuelle: cargo test"),
        "{text}"
    );
    assert!(!text.contains("global"), "{text}");
    let none = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(["--scope", "p", "journal-search", db, "nichtvorhanden"])
        .output()
        .unwrap();
    assert!(
        String::from_utf8(none.stdout)
            .unwrap()
            .contains("Keine Tagebucheinträge gefunden.")
    );
}

#[test]
fn invalid_journal_search_limit_is_rejected_before_the_database_is_opened() {
    let temp = Temp::new();
    let missing = temp.0.join("fehlt.db");
    let broken = temp.0.join("kaputt.db");
    std::fs::write(&broken, b"kein SQLite").unwrap();
    for path in [&missing, &broken] {
        for bad in ["0", "21", "fünf"] {
            let out = Command::new(env!("CARGO_BIN_EXE_vmind"))
                .args([
                    "journal-search",
                    path.to_str().unwrap(),
                    "x",
                    "--limit",
                    bad,
                ])
                .output()
                .unwrap();
            assert!(!out.status.success(), "--limit {bad} angenommen");
            let message = String::from_utf8_lossy(&out.stderr);
            assert!(message.contains("Limit muss 1 bis 20 sein"), "{message}");
        }
    }
    assert!(!missing.exists(), "fehlende Datenbank wurde angelegt");
    assert_eq!(std::fs::read(&broken).unwrap(), b"kein SQLite");
}
#[test]
fn journal_search_never_upgrades_or_backs_up_an_older_database() {
    let temp = Temp::new();
    let path = temp.0.join("v5.db");
    {
        let c = rusqlite::Connection::open(&path).unwrap();
        for sql in [
            include_str!("../../../migrations/0001_memory.sql"),
            include_str!("../../../migrations/0002_retrieval.sql"),
            include_str!("../../../migrations/0003_project_context.sql"),
            include_str!("../../../migrations/0004_checks.sql"),
            include_str!("../../../migrations/0005_partial_search.sql"),
        ] {
            c.execute_batch(sql).unwrap();
        }
        c.pragma_update(None, "user_version", 5).unwrap();
        c.execute(
            "INSERT INTO project_journal(scope,kind,body,source) VALUES('p','note','alter Eintrag','Test')",
            [],
        )
        .unwrap();
    }
    let before = std::fs::read(&path).unwrap();
    let db = path.to_str().unwrap();
    for args in [
        vec!["--scope", "p", "journal-search", db, "Eintrag"],
        vec![
            "--scope",
            "p",
            "journal-search",
            db,
            "Eintrag",
            "--limit",
            "3",
        ],
    ] {
        let (ok, _) = cli_status(&args);
        assert!(!ok, "Schema 5 wird nicht still umgestellt: {args:?}");
    }
    assert_eq!(std::fs::read(&path).unwrap(), before, "Datei unverändert");
    let files: Vec<String> = std::fs::read_dir(&temp.0)
        .unwrap()
        .map(|e| e.unwrap().file_name().to_string_lossy().into_owned())
        .collect();
    assert_eq!(files, ["v5.db"], "keine Sicherung und keine Zusatzdateien");
}
fn nudge(db: &str, scope: &str, input: &str) -> (bool, String) {
    use std::io::Write;
    let mut child = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(["--scope", scope, "nudge", db])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    // Ein Hook darf auch bei vorzeitig geschlossener Eingabe nicht scheitern.
    let _ = child.stdin.take().unwrap().write_all(input.as_bytes());
    let out = child.wait_with_output().unwrap();
    (out.status.success(), String::from_utf8(out.stdout).unwrap())
}
fn prompt_event() -> String {
    serde_json::json!({"session_id":"s1","hook_event_name":"UserPromptSubmit","cwd":"/projekt",
        "prompt":"GEHEIMER-PROMPT"})
    .to_string()
}
fn assert_nudge_silent(db: &str, input: &str) {
    let (ok, out) = nudge(db, "p", input);
    assert!(ok, "Hook muss erfolgreich enden: {input}");
    assert!(out.is_empty(), "keine Ausgabe erwartet bei {input}: {out}");
}
#[test]
fn nudge_hook_returns_counts_only_without_prompt_or_stored_text_and_without_writing() {
    let temp = Temp::new();
    let path = temp.0.join("nudge.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    cli(&[
        "--scope",
        "p",
        "log",
        db,
        "next_step",
        "GEHEIMER-SCHRITT",
        "GEHEIME-QUELLE",
    ]);
    cli(&[
        "--scope",
        "p",
        "task",
        db,
        "geheimer-schluessel",
        "in_progress",
        "GEHEIME-AUFGABE",
        "GEHEIME-QUELLE",
    ]);
    cli(&[
        "--scope",
        "p",
        "add",
        db,
        "error_solution",
        "GEHEIMES-PROBLEM",
        "GEHEIME-LOESUNG",
        "GEHEIME-QUELLE",
    ]);
    let before = std::fs::read(&path).unwrap();

    let (ok, out) = nudge(db, "p", &prompt_event());

    assert!(ok);
    assert_eq!(out.trim_end().lines().count(), 1, "eine Zeile: {out}");
    assert!(!out.contains("GEHEIM"), "kein Inhalt in der Ausgabe: {out}");
    assert!(!out.contains("geheimer-schluessel"), "{out}");
    let answer: Value = serde_json::from_str(&out).unwrap();
    assert_eq!(
        answer["hookSpecificOutput"]["hookEventName"],
        "UserPromptSubmit"
    );
    let context = answer["hookSpecificOutput"]["additionalContext"]
        .as_str()
        .unwrap();
    assert!(context.starts_with("V-Mind: Vor der Arbeit journal_search"));
    assert!(context.contains("in Arbeit oder blockiert: 1"), "{context}");
    assert!(context.contains("ungeprüfte Einträge: 1"), "{context}");
    assert!(context.contains("überholt"), "{context}");
    assert!(context.chars().count() <= 300, "{context}");
    assert_eq!(
        std::fs::read(&path).unwrap(),
        before,
        "Datenbank unverändert"
    );
}
#[test]
fn nudge_hook_shows_the_reminder_for_a_database_without_open_work() {
    let temp = Temp::new();
    let path = temp.0.join("leer.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);

    let (ok, out) = nudge(db, "p", &prompt_event());

    assert!(ok);
    let answer: Value = serde_json::from_str(&out).unwrap();
    assert_eq!(
        answer["hookSpecificOutput"]["additionalContext"],
        "V-Mind: Vor der Arbeit journal_search zum Thema und recall für Wissen nutzen."
    );
}
#[test]
fn nudge_hook_stays_silent_and_successful_on_every_failure_path() {
    let temp = Temp::new();
    let path = temp.0.join("still.db");
    let db = path.to_str().unwrap();
    cli(&["init", db]);
    let before = std::fs::read(&path).unwrap();
    assert_nudge_silent(db, "");
    assert_nudge_silent(db, "kein json");
    assert_nudge_silent(db, r#"{"prompt":"ohne Ereignis"}"#);
    assert_nudge_silent(db, r#"{"hook_event_name":"PostToolUse","prompt":"x"}"#);
    assert_eq!(std::fs::read(&path).unwrap(), before, "Datei unverändert");
    let missing = temp.0.join("fehlt.db");
    assert_nudge_silent(missing.to_str().unwrap(), &prompt_event());
    assert!(!missing.exists(), "Hook legt keine Datenbank an");
}
#[test]
fn nudge_hook_never_upgrades_or_backs_up_an_older_database() {
    let temp = Temp::new();
    let path = temp.0.join("v5.db");
    {
        let c = rusqlite::Connection::open(&path).unwrap();
        for sql in [
            include_str!("../../../migrations/0001_memory.sql"),
            include_str!("../../../migrations/0002_retrieval.sql"),
            include_str!("../../../migrations/0003_project_context.sql"),
            include_str!("../../../migrations/0004_checks.sql"),
            include_str!("../../../migrations/0005_partial_search.sql"),
        ] {
            c.execute_batch(sql).unwrap();
        }
        c.pragma_update(None, "user_version", 5).unwrap();
    }
    let before = std::fs::read(&path).unwrap();

    assert_nudge_silent(path.to_str().unwrap(), &prompt_event());

    assert_eq!(std::fs::read(&path).unwrap(), before, "Datei unverändert");
    let files: Vec<String> = std::fs::read_dir(&temp.0)
        .unwrap()
        .map(|e| e.unwrap().file_name().to_string_lossy().into_owned())
        .collect();
    assert_eq!(files, ["v5.db"], "keine Sicherung und keine Zusatzdateien");
}
