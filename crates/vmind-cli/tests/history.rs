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
    fs::write(&bad, "[1,2]\n").unwrap();
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
    fs::write(&file, "[1,2]\n").unwrap();
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

fn transcript_with_corrupt_line(path: &str) -> u64 {
    let row = |uuid: &str, text: &str| {
        json!({"type":"user","uuid":uuid,"sessionId":"zeile","timestamp":"2026-01-01T00:00:00.000Z",
            "message":{"role":"user","content":text}})
    };
    let first = format!("{}\n", row("u1", "vor Schaden"));
    let second = format!("{}\n", row("u2", "nach Schaden"));
    fs::write(path, format!("{first}{{\"DEFEKTINHALT\n{second}")).unwrap();
    first.len() as u64
}

#[test]
fn hook_skips_a_corrupt_line_silently_and_status_keeps_the_warning() {
    let t = Temp::new();
    let (db, file) = (t.path("v.db"), t.path("s.jsonl"));
    init(&db);
    let position = transcript_with_corrupt_line(&file);
    for _ in 0..2 {
        assert_silent(&hook(&db, &event("Stop", &file)));
        let report = status(&db);
        assert_eq!(report["messages"], 2);
        assert_eq!(report["failed"], 0);
        assert_eq!(report["sources"][0]["corrupt_lines"], 1);
        assert_eq!(report["sources"][0]["last_error"], Value::Null);
        let warning = report["sources"][0]["warning"].as_str().unwrap();
        assert!(warning.contains(&format!("Byte {position}")), "{warning}");
        assert!(!warning.contains("DEFEKTINHALT"));
    }
    let human = run(&["--scope", "p", "history-status", &db], "");
    let text = String::from_utf8(human.stdout).unwrap();
    assert!(text.contains("WARNUNG"), "{text}");
    assert!(text.contains(&format!("Byte {position}")), "{text}");
    assert!(text.contains("Quellen mit Warnung: 1"), "{text}");
    assert!(!text.contains("DEFEKTINHALT"), "{text}");
}

#[test]
fn import_tool_succeeds_and_names_skipped_lines() {
    let t = Temp::new();
    let (db, file) = (t.path("v.db"), t.path("s.jsonl"));
    init(&db);
    transcript_with_corrupt_line(&file);
    let out = run(&["--scope", "p", "history-import", &db, &file], "");
    assert!(out.status.success());
    let text = String::from_utf8(out.stdout).unwrap();
    assert!(text.contains("WARNUNG"), "{text}");
}

#[test]
fn unknown_structure_still_stops_the_hook_silently_with_a_recorded_error() {
    let t = Temp::new();
    let (db, file) = (t.path("v.db"), t.path("s.jsonl"));
    init(&db);
    fs::write(&file, "[1,2]\n").unwrap();
    assert_silent(&hook(&db, &event("Stop", &file)));
    let report = status(&db);
    assert_eq!(report["failed"], 1);
    assert_eq!(report["messages"], 0);
    assert_eq!(report["sources"][0]["byte_offset"], 0);
    assert_eq!(report["sources"][0]["corrupt_lines"], 0);
}

const CODEX_SESSION: &str = "00000000-0000-7000-8000-0000000000cc";

fn codex_rollout(path: &str, text: &str) {
    let rows = [
        json!({"timestamp":"2026-01-02T03:04:05.000Z","type":"session_meta",
            "payload":{"id":CODEX_SESSION}}),
        json!({"timestamp":"2026-01-02T03:04:05.000Z","type":"turn_context",
            "payload":{"turn_id":"t1","model":"modell-beispiel"}}),
        json!({"timestamp":"2026-01-02T03:04:06.000Z","ordinal":2,"type":"event_msg",
            "payload":{"type":"item_completed","turn_id":"t1","item":{"type":"AgentMessage",
                "id":"a1","phase":"final_answer","content":[{"type":"Text","text":text}]}}}),
    ];
    fs::write(
        path,
        rows.iter().map(|r| format!("{r}\n")).collect::<String>(),
    )
    .unwrap();
}

/// Wie `run`, aber ohne geerbten Standardbereich aus der Umgebung.
fn run_without_scope_env(args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_vmind"))
        .args(args)
        .env_remove("VMIND_SCOPE")
        .output()
        .unwrap()
}

#[test]
fn codex_import_needs_an_explicit_scope_and_a_known_tool() {
    let t = Temp::new();
    let (db, file) = (t.path("v.db"), t.path("rollout.jsonl"));
    init(&db);
    codex_rollout(&file, "Seestern");
    let without = run_without_scope_env(&["history-import", &db, &file, "--tool", "codex"]);
    assert!(!without.status.success());
    assert!(String::from_utf8_lossy(&without.stderr).contains("--scope"));
    let unknown = run(
        &[
            "--scope",
            "p",
            "history-import",
            &db,
            &file,
            "--tool",
            "hermes",
        ],
        "",
    );
    assert!(!unknown.status.success());
    assert_eq!(status(&db)["sources"].as_array().unwrap().len(), 0);
    let report = json_of(&[
        "--scope",
        "p",
        "history-import",
        &db,
        &file,
        "--tool",
        "codex",
    ]);
    assert_eq!(report["added"], 1);
    assert_eq!(report["tool"], "codex");
    assert_eq!(status(&db)["sources"][0]["tool"], "codex");
}

#[test]
fn hits_show_tool_and_model_and_can_be_filtered_everywhere() {
    let t = Temp::new();
    let (db, codex, claude) = (t.path("v.db"), t.path("r.jsonl"), t.path("c.jsonl"));
    init(&db);
    codex_rollout(&codex, "Seepferdchen aus Codex");
    transcript(&claude, "Seepferdchen aus Claude");
    json_of(&[
        "--scope",
        "p",
        "history-import",
        &db,
        &codex,
        "--tool",
        "codex",
    ]);
    json_of(&["--scope", "p", "history-import", &db, &claude]);

    let all = json_of(&["--scope", "p", "history-search", &db, "seepferdchen"]);
    assert_eq!(all["hits"].as_array().unwrap().len(), 2);
    let only = json_of(&[
        "--scope",
        "p",
        "history-search",
        &db,
        "seepferdchen",
        "--tool",
        "codex",
        "--limit",
        "3",
    ]);
    let hits = only["hits"].as_array().unwrap();
    assert_eq!(hits.len(), 1);
    assert_eq!(hits[0]["tool"], "codex");
    assert_eq!(hits[0]["model"], "modell-beispiel");
    let human = run(
        &[
            "--scope",
            "p",
            "history-search",
            &db,
            "seepferdchen",
            "--tool",
            "claude-code",
        ],
        "",
    );
    let text = String::from_utf8(human.stdout).unwrap();
    assert!(text.contains("claude-code"), "{text}");
    assert!(!text.contains("aus Codex"), "{text}");
    let bad = run(
        &[
            "--scope",
            "p",
            "history-search",
            &db,
            "x",
            "--tool",
            "hermes",
        ],
        "",
    );
    assert!(!bad.status.success());

    let jsonl = run(
        &["serve", &db],
        &format!(
            "{}\n{}\n",
            json!({"id":1,"op":"history_search","scope":"p","query":"seepferdchen","tool":"codex"}),
            json!({"id":2,"op":"history_search","scope":"p","query":"x","tool":"hermes"}),
        ),
    );
    let lines: Vec<Value> = String::from_utf8(jsonl.stdout)
        .unwrap()
        .lines()
        .map(|l| serde_json::from_str(l).unwrap())
        .collect();
    let hits = lines[0]["data"]["hits"].as_array().unwrap();
    assert_eq!(hits.len(), 1);
    assert_eq!(hits[0]["tool"], "codex");
    assert_eq!(lines[1]["ok"], false);

    let call = json!({"jsonrpc":"2.0","id":1,"method":"tools/call","params":{
        "name":"history_search","arguments":{"query":"seepferdchen","tool":"claude-code"}}});
    let mcp = run(&["--scope", "p", "mcp", &db], &format!("{call}\n"));
    let line: Value = serde_json::from_slice(&mcp.stdout).unwrap();
    let payload: Value =
        serde_json::from_str(line["result"]["content"][0]["text"].as_str().unwrap()).unwrap();
    let hits = payload["hits"].as_array().unwrap();
    assert_eq!(hits.len(), 1);
    assert_eq!(hits[0]["tool"], "claude-code");
    assert_eq!(hits[0]["model"], Value::Null);
}

/// Synthetischer OpenCode-Snapshot (Schema laut Formatbefund) mit einer Sitzung.
fn opencode_snapshot(path: &str, text: &str) {
    let c = rusqlite::Connection::open(path).unwrap();
    c.pragma_update(None, "journal_mode", "WAL").unwrap();
    c.execute_batch(
        "CREATE TABLE session(id TEXT PRIMARY KEY, parent_id TEXT, directory TEXT);
         CREATE TABLE message(id TEXT PRIMARY KEY, session_id TEXT, time_created INTEGER,
             time_updated INTEGER, data TEXT);
         CREATE TABLE part(id TEXT PRIMARY KEY, message_id TEXT, session_id TEXT,
             time_created INTEGER, time_updated INTEGER, data TEXT);
         INSERT INTO session VALUES('ses_cli', NULL, '/beispiel');",
    )
    .unwrap();
    let data = json!({"role":"assistant","time":{"created":1767323047000_i64,
        "completed":1767323050000_i64},"providerID":"anbieter-a","modelID":"modell-a"});
    c.execute(
        "INSERT INTO message VALUES('msg_cli', 'ses_cli', 1767323047000, 1767323047000, ?1)",
        [data.to_string()],
    )
    .unwrap();
    for (id, part) in [
        ("prt_1", json!({"type":"text","text":text})),
        (
            "prt_2",
            json!({"type":"reasoning","text":"Gedanke Tintenfisch"}),
        ),
    ] {
        c.execute(
            "INSERT INTO part VALUES(?1, 'msg_cli', 'ses_cli', 0, 0, ?2)",
            [id, &part.to_string()],
        )
        .unwrap();
    }
    c.close().unwrap();
}

#[test]
fn opencode_import_reads_a_snapshot_and_is_searchable_everywhere() {
    let t = Temp::new();
    let (db, snap) = (t.path("v.db"), t.path("opencode snapshot.db"));
    init(&db);
    opencode_snapshot(&snap, "Tintenfisch aus OpenCode");
    let before = fs::read(&snap).unwrap();
    let import = |extra: &[&str]| {
        let mut args = vec!["--scope", "p", "history-import", &db, &snap];
        args.extend(extra);
        args.iter().map(|a| a.to_string()).collect::<Vec<_>>()
    };

    let without = run_without_scope_env(&["history-import", &db, &snap, "--tool", "opencode"]);
    assert!(!without.status.success());
    assert!(String::from_utf8_lossy(&without.stderr).contains("--scope"));
    let session_for_codex = run(
        &[
            "--scope",
            "p",
            "history-import",
            &db,
            &snap,
            "--session",
            "ses_cli",
        ],
        "",
    );
    assert!(!session_for_codex.status.success());
    assert!(String::from_utf8_lossy(&session_for_codex.stderr).contains("--session"));

    let args = import(&["--tool", "opencode", "--session", "ses_cli"]);
    let refs: Vec<&str> = args.iter().map(String::as_str).collect();
    let report = json_of(&refs);
    assert_eq!(
        (report["added"].clone(), report["tool"].clone()),
        (json!(1), json!("opencode"))
    );
    assert_eq!(report["error"], Value::Null);
    let again = json_of(&refs);
    assert_eq!(again["added"], 0, "dedupliziert");
    assert_eq!(status(&db)["sources"][0]["tool"], "opencode");
    let human = run(&refs, "");
    assert!(String::from_utf8_lossy(&human.stdout).contains("Snapshot"));

    let only = json_of(&[
        "--scope",
        "p",
        "history-search",
        &db,
        "tintenfisch",
        "--tool",
        "opencode",
    ]);
    let hits = only["hits"].as_array().unwrap();
    assert_eq!(hits.len(), 1, "Reasoning nicht übernommen");
    assert_eq!(hits[0]["model"], "anbieter-a/modell-a");
    assert_eq!(hits[0]["created_at"], "2026-01-02T03:04:07.000Z");
    assert_eq!(hits[0]["uuid"], "opencode:ses_cli:msg_cli");

    let jsonl = run(
        &["serve", &db],
        &format!(
            "{}\n",
            json!({"id":1,"op":"history_search","scope":"p","query":"tintenfisch","tool":"opencode"})
        ),
    );
    let line: Value = serde_json::from_slice(&jsonl.stdout).unwrap();
    assert_eq!(line["data"]["hits"][0]["tool"], "opencode");
    let call = json!({"jsonrpc":"2.0","id":1,"method":"tools/call","params":{
        "name":"history_search","arguments":{"query":"tintenfisch","tool":"opencode"}}});
    let mcp = run(&["--scope", "p", "mcp", &db], &format!("{call}\n"));
    let line: Value = serde_json::from_slice(&mcp.stdout).unwrap();
    let payload: Value =
        serde_json::from_str(line["result"]["content"][0]["text"].as_str().unwrap()).unwrap();
    assert_eq!(payload["hits"][0]["tool"], "opencode");

    assert_eq!(fs::read(&snap).unwrap(), before, "Quelle unverändert");
    for suffix in ["-wal", "-shm", "-journal"] {
        assert!(!Path::new(&format!("{snap}{suffix}")).exists(), "{suffix}");
    }
    fs::write(format!("{snap}-wal"), b"aktiv").unwrap();
    let blocked = run(&refs, "");
    assert!(!blocked.status.success());
    assert!(String::from_utf8_lossy(&blocked.stdout).contains("WAL"));
}

/// Symbolischer und harter Link auf die Datenbank; unter Windows nicht erkannt bzw. nicht
/// ohne Sonderrechte anlegbar, daher nur unter Unix.
#[cfg(unix)]
fn link_aliases(t: &Temp, db: &str) -> Vec<String> {
    let (link, hard) = (t.path("verweis.db"), t.path("hart.db"));
    std::os::unix::fs::symlink(db, &link).unwrap();
    fs::hard_link(db, &hard).unwrap();
    vec![link, hard]
}

#[cfg(not(unix))]
fn link_aliases(_: &Temp, _: &str) -> Vec<String> {
    Vec::new()
}

/// Die eigene Datenbank als Quelle: Exit 1, Datei byte-gleich, keine Sidecars, kein
/// Fehlereintrag; auch über Pfadumweg, symbolischen und harten Link.
#[test]
fn opencode_import_of_the_database_itself_changes_nothing() {
    let t = Temp::new();
    let db = t.path("v.db");
    init(&db);
    let aliases = [
        vec![
            db.clone(),
            t.0.join(".").join("v.db").to_str().unwrap().to_owned(),
        ],
        link_aliases(&t, &db),
    ]
    .concat();
    let before = fs::read(&db).unwrap();
    for source in &aliases {
        let out = run(
            &[
                "--scope",
                "p",
                "history-import",
                &db,
                source,
                "--tool",
                "opencode",
            ],
            "",
        );
        assert!(!out.status.success(), "{source}");
        assert!(
            String::from_utf8_lossy(&out.stderr).contains("V-Mind-Datenbank"),
            "{source}"
        );
        assert_eq!(
            fs::read(&db).unwrap(),
            before,
            "Ziel verändert über {source}"
        );
        for suffix in ["-wal", "-shm", "-journal"] {
            assert!(!Path::new(&format!("{db}{suffix}")).exists(), "{suffix}");
        }
    }
    assert_eq!(status(&db)["failed"], 0, "kein Fehlereintrag");
}
