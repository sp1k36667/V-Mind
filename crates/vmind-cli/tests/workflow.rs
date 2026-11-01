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
    assert!(
        replies[1]["data"]["memories"]
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
    let shown = cli(&["show", db, &id]);
    assert_eq!(shown["check"]["argv"][2], "test -f marker");
    assert_eq!(shown["check_runs"].as_array().unwrap().len(), 2);

    assert!(cli(&["--scope", "p", "revalidate", db])["failed"] == 0);
    std::fs::remove_file(workdir.join("marker")).unwrap();
    let (passed, report) = cli_status(&["--scope", "p", "revalidate", db]);
    assert!(!passed);
    assert_eq!(report["results"][0]["status_after"], "validated");
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
