//! Verlaufs-Befehle über das echte Programm; nur synthetische JSONL-Dateien.
use serde_json::{Value, json};
use std::{
    fs,
    io::Write,
    path::{Path, PathBuf},
    process::{Command, Output, Stdio},
};

struct Temp(PathBuf);
impl Temp {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "vmind-cli-history-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir(&path).unwrap();
        Self(path)
    }
    fn path(&self, name: &str) -> String {
        self.0.join(name).to_str().unwrap().to_owned()
    }
}
impl Drop for Temp {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn run(args: &[&str], stdin: &str) -> Output {
    let mut child = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(stdin.as_bytes())
        .unwrap();
    child.wait_with_output().unwrap()
}
fn json_of(args: &[&str]) -> Value {
    let mut all = vec!["--json"];
    all.extend(args);
    let out = run(&all, "");
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    serde_json::from_slice(&out.stdout).unwrap()
}
fn init(db: &str) {
    assert!(run(&["init", db], "").status.success());
}
fn transcript(path: &str, text: &str) {
    let row = json!({"type":"user","uuid":"u1","sessionId":"zeile","timestamp":"2026-01-01T00:00:00.000Z",
        "message":{"role":"user","content":text}});
    fs::write(path, format!("{row}\n")).unwrap();
}
fn hook(db: &str, input: &str) -> Output {
    run(&["--scope", "p", "history-hook", db], input)
}
fn event(name: &str, path: &str) -> String {
    json!({"hook_event_name":name,"transcript_path":path,"session_id":"haken"}).to_string()
}
fn assert_silent(out: &Output) {
    assert!(out.status.success(), "Exit 0 erwartet");
    assert!(out.stdout.is_empty(), "nichts auf stdout");
}
fn status(db: &str) -> Value {
    json_of(&["--scope", "p", "history-status", db])
}

#[test]
fn stop_and_pre_compact_import_incrementally_and_search_finds_the_text() {
    let t = Temp::new();
    let (db, file) = (t.path("v.db"), t.path("s.jsonl"));
    init(&db);
    transcript(&file, "Marmelade im Keller");
    assert_silent(&hook(&db, &event("Stop", &file)));
    assert_silent(&hook(&db, &event("PreCompact", &file)));
    let found = json_of(&["--scope", "p", "history-search", &db, "marmelade"]);
    assert_eq!(found["status"], "unverified_history");
    let hits = found["hits"].as_array().unwrap();
    assert_eq!(hits.len(), 1);
    assert_eq!(hits[0]["text"], "Marmelade im Keller");
    assert_eq!(hits[0]["status"], "unverified");
    let report = status(&db);
    assert_eq!(report["messages"], 1);
    assert_eq!(report["failed"], 0);
    assert_eq!(report["sources"][0]["source_path"], file.as_str());
    let human = run(&["--scope", "p", "history-search", &db, "marmelade"], "");
    let text = String::from_utf8(human.stdout).unwrap();
    assert!(text.contains("UNVERIFIZIERTER VERLAUF"), "{text}");
}

#[test]
fn other_events_do_nothing() {
    let t = Temp::new();
    let (db, file) = (t.path("v.db"), t.path("s.jsonl"));
    init(&db);
    transcript(&file, "Anderes Ereignis");
    assert_silent(&hook(&db, &event("PostToolUse", &file)));
    assert_eq!(status(&db)["messages"], 0);
    assert_eq!(status(&db)["sources"].as_array().unwrap().len(), 0);
}

#[test]
fn every_failure_path_is_silent_and_recorded_when_a_database_exists() {
    let t = Temp::new();
    let (db, file) = (t.path("v.db"), t.path("s.jsonl"));
    init(&db);
    transcript(&file, "x");
    for (input, reason) in [
        ("kein json".to_owned(), "(hook)"),
        (
            json!({"hook_event_name":"Stop","session_id":"s"}).to_string(),
            "(hook)",
        ),
        (
            json!({"hook_event_name":"Stop","transcript_path":file}).to_string(),
            "(hook)",
        ),
    ] {
        assert_silent(&hook(&db, &input));
        assert_eq!(status(&db)["sources"][0]["source_path"], reason);
        assert_eq!(status(&db)["failed"], 1);
    }
    let not_jsonl = t.path("s.txt");
    fs::write(&not_jsonl, "x").unwrap();
    assert_silent(&hook(&db, &event("Stop", &not_jsonl)));
    let missing = t.path("fehlt.jsonl");
    assert_silent(&hook(&db, &event("Stop", &missing)));
    let bad = t.path("kaputt.jsonl");
    fs::write(&bad, "kein json\n").unwrap();
    assert_silent(&hook(&db, &event("Stop", &bad)));
    let report = status(&db);
    assert_eq!(report["failed"], 4);
    assert_eq!(report["messages"], 0);
    let oversized = "x".repeat(1_048_577);
    assert_silent(&hook(&db, &oversized));
}

#[test]
fn hook_without_database_creates_nothing() {
    let t = Temp::new();
    let (db, file) = (t.path("fehlt.db"), t.path("s.jsonl"));
    transcript(&file, "x");
    assert_silent(&hook(&db, &event("Stop", &file)));
    assert!(!Path::new(&db).exists());
}

#[test]
fn hook_never_upgrades_or_backs_up_an_older_database() {
    let t = Temp::new();
    let (db, file) = (t.path("v6.db"), t.path("s.jsonl"));
    {
        let c = rusqlite::Connection::open(&db).unwrap();
        for sql in [
            include_str!("../../../migrations/0001_memory.sql"),
            include_str!("../../../migrations/0002_retrieval.sql"),
            include_str!("../../../migrations/0003_project_context.sql"),
            include_str!("../../../migrations/0004_checks.sql"),
            include_str!("../../../migrations/0005_partial_search.sql"),
            include_str!("../../../migrations/0006_observations.sql"),
        ] {
            c.execute_batch(sql).unwrap();
        }
        c.pragma_update(None, "user_version", 6).unwrap();
    }
    transcript(&file, "x");
    let before = fs::read(&db).unwrap();
    assert_silent(&hook(&db, &event("Stop", &file)));
    assert_eq!(fs::read(&db).unwrap(), before, "Datei unverändert");
    let backups = fs::read_dir(&t.0)
        .unwrap()
        .filter(|e| {
            e.as_ref()
                .unwrap()
                .file_name()
                .to_string_lossy()
                .contains("before-schema")
        })
        .count();
    assert_eq!(backups, 0);
    // Auch Suche und Status stellen nichts um.
    assert!(
        !run(&["--scope", "p", "history-search", &db, "x"], "")
            .status
            .success()
    );
    assert!(
        !run(&["--scope", "p", "history-status", &db], "")
            .status
            .success()
    );
    assert_eq!(fs::read(&db).unwrap(), before);
}

#[test]
fn import_tool_reports_counts_and_fails_visibly() {
    let t = Temp::new();
    let (db, file) = (t.path("v.db"), t.path("s.jsonl"));
    init(&db);
    transcript(&file, "Werkzeuglauf");
    let report = json_of(&["--scope", "p", "history-import", &db, &file]);
    assert_eq!(report["added"], 1);
    assert_eq!(report["error"], Value::Null);
    fs::write(&file, "kein json\n").unwrap();
    let failed = run(&["--scope", "p", "history-import", &db, &file], "");
    assert!(!failed.status.success());
    assert_eq!(status(&db)["failed"], 1);
}

#[test]
fn invalid_limit_is_rejected_before_the_database_is_opened() {
    let t = Temp::new();
    let db = t.path("fehlt.db");
    for limit in ["0", "21", "x"] {
        let out = run(
            &["--scope", "p", "history-search", &db, "x", "--limit", limit],
            "",
        );
        assert!(!out.status.success());
        assert!(String::from_utf8_lossy(&out.stderr).contains("Limit"));
    }
}

#[test]
fn jsonl_and_mcp_offer_history_search_with_the_exact_scope() {
    let t = Temp::new();
    let (db, file) = (t.path("v.db"), t.path("s.jsonl"));
    init(&db);
    transcript(&file, "Leuchtturm am Meer");
    json_of(&["--scope", "p", "history-import", &db, &file]);

    let jsonl = run(
        &["serve", &db],
        &format!(
            "{}\n{}\n{}\n",
            json!({"id":1,"op":"history_search","scope":"p","query":"leuchtturm"}),
            json!({"id":2,"op":"history_search","scope":"global","query":"leuchtturm"}),
            json!({"id":3,"op":"history_search","scope":"p","query":"x","limit":21}),
        ),
    );
    let lines: Vec<Value> = String::from_utf8(jsonl.stdout)
        .unwrap()
        .lines()
        .map(|l| serde_json::from_str(l).unwrap())
        .collect();
    assert_eq!(lines[0]["data"]["hits"][0]["text"], "Leuchtturm am Meer");
    assert_eq!(lines[0]["data"]["status"], "unverified_history");
    assert_eq!(lines[1]["data"]["hits"].as_array().unwrap().len(), 0);
    assert_eq!(lines[2]["ok"], false);

    let call = json!({"jsonrpc":"2.0","id":1,"method":"tools/call","params":{
        "name":"history_search","arguments":{"query":"leuchtturm"}}});
    let list = json!({"jsonrpc":"2.0","id":2,"method":"tools/list"});
    let mcp = run(&["--scope", "p", "mcp", &db], &format!("{call}\n{list}\n"));
    let lines: Vec<Value> = String::from_utf8(mcp.stdout)
        .unwrap()
        .lines()
        .map(|l| serde_json::from_str(l).unwrap())
        .collect();
    let payload: Value =
        serde_json::from_str(lines[0]["result"]["content"][0]["text"].as_str().unwrap()).unwrap();
    assert_eq!(payload["hits"][0]["scope"], "p");
    assert!(
        lines[1]["result"]["tools"]
            .as_array()
            .unwrap()
            .iter()
            .any(|tool| tool["name"] == "history_search")
    );
}

#[test]
fn audit_secrets_scans_the_history_tables() {
    let t = Temp::new();
    let db = t.path("v.db");
    init(&db);
    let report = json_of(&["audit-secrets", &db]);
    let tables: Vec<&str> = report["scanned"]
        .as_array()
        .unwrap()
        .iter()
        .map(|s| s["table"].as_str().unwrap())
        .collect();
    assert!(tables.contains(&"history_messages"), "{tables:?}");
    assert!(tables.contains(&"history_imports"), "{tables:?}");
}
