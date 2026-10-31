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
