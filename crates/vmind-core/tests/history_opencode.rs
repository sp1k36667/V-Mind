//! OpenCode-Verlaufsimport aus einem SQLite-Snapshot (ab Schema 9): nur synthetische
//! Datenbanken nach dem Formatbefund zu OpenCode 1.18.15, keine echten Nutzerdaten.
use rusqlite::{Connection, params};
use serde_json::{Value, json};
use std::{
    fs,
    path::{Path, PathBuf},
};
use vmind_core::{HistoryHit, HistoryImport, HistoryTool, MemoryStore};

const SESSION: &str = "ses_synth01";
const SCHEMA: &str = "
    CREATE TABLE session(id TEXT PRIMARY KEY, project_id TEXT, parent_id TEXT, directory TEXT,
        title TEXT, time_created INTEGER, time_updated INTEGER, time_archived INTEGER);
    CREATE TABLE message(id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
        time_created INTEGER NOT NULL, time_updated INTEGER NOT NULL, data TEXT NOT NULL);
    CREATE TABLE part(id TEXT PRIMARY KEY, message_id TEXT NOT NULL, session_id TEXT NOT NULL,
        time_created INTEGER NOT NULL, time_updated INTEGER NOT NULL, data TEXT NOT NULL);";

struct Temp(PathBuf);
impl Temp {
    fn new() -> Self {
        let p = std::env::temp_dir().join(format!(
            "vmind-opencode-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir(&p).unwrap();
        Self(p)
    }
    fn db(&self) -> PathBuf {
        self.0.join("v.db")
    }
    fn source(&self) -> PathBuf {
        self.0.join("opencode-snapshot.db")
    }
    fn store(&self) -> MemoryStore {
        MemoryStore::open_file(self.db()).unwrap()
    }
}
impl Drop for Temp {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn sidecar(path: &Path, suffix: &str) -> PathBuf {
    let mut name = path.as_os_str().to_owned();
    name.push(suffix);
    PathBuf::from(name)
}

fn sidecars(path: &Path) -> Vec<PathBuf> {
    ["-wal", "-shm", "-journal"]
        .iter()
        .map(|s| sidecar(path, s))
        .filter(|p| p.exists())
        .collect()
}

/// Synthetische OpenCode-Datenbank im WAL-Modus; nach dem Schließen ohne Sidecars.
struct Source(Connection);
impl Source {
    fn create(path: &Path) -> Self {
        let c = Connection::open(path).unwrap();
        c.pragma_update(None, "journal_mode", "WAL").unwrap();
        c.execute_batch(SCHEMA).unwrap();
        let s = Self(c);
        s.session(SESSION, None);
        s
    }
    fn session(&self, id: &str, parent: Option<&str>) {
        self.0
            .execute(
                "INSERT INTO session(id, project_id, parent_id, directory, title, time_created,
                 time_updated) VALUES(?1, 'prj_synth01', ?2, '/beispiel/projekt', 'Synthetisch',
                 1767323040000, 1767323170000)",
                params![id, parent],
            )
            .unwrap();
    }
    fn message(&self, id: &str, session: &str, created: i64, data: Value) {
        self.0
            .execute(
                "INSERT INTO message(id, session_id, time_created, time_updated, data)
                 VALUES(?1, ?2, ?3, ?3, ?4)",
                params![id, session, created, data.to_string()],
            )
            .unwrap();
    }
    fn part(&self, id: &str, message: &str, session: &str, data: Value) {
        self.0
            .execute(
                "INSERT INTO part(id, message_id, session_id, time_created, time_updated, data)
                 VALUES(?1, ?2, ?3, 0, 0, ?4)",
                params![id, message, session, data.to_string()],
            )
            .unwrap();
    }
    fn close(self) {
        self.0.close().unwrap();
    }
}

fn user_data(created: i64, model: Option<(&str, &str)>) -> Value {
    let mut data = json!({"role":"user","time":{"created":created},"agent":"build"});
    if let Some((provider, model)) = model {
        data["model"] = json!({"providerID":provider,"modelID":model});
    }
    data
}

fn assistant_data(created: i64, model: Option<(&str, &str)>) -> Value {
    let mut data = json!({"role":"assistant","time":{"created":created,"completed":created+1000},
        "mode":"build","agent":"build","path":{"cwd":"/beispiel/projekt","root":"/beispiel/projekt"},
        "cost":0,"finish":"stop"});
    if let Some((provider, model)) = model {
        data["providerID"] = json!(provider);
        data["modelID"] = json!(model);
    }
    data
}

fn text(value: &str) -> Value {
    json!({"type":"text","text":value})
}

/// Nachbildung von `export-ses_synth01.json` aus dem Formatbefund.
fn fill_example(s: &Source) {
    let a = Some(("anbieter-a", "modell-a"));
    let b = Some(("anbieter-b", "modell-b"));
    let mut user = user_data(1767323046000, a);
    user["system"] = json!("Eigener Systemtext, nicht importieren");
    s.message("msg_synth0001", SESSION, 1767323046000, user);
    s.part(
        "prt_synth0001",
        "msg_synth0001",
        SESSION,
        text("Wie heisst die Testkatze?"),
    );
    s.part(
        "prt_synth0002",
        "msg_synth0001",
        SESSION,
        json!({"type":"text","text":"Vom Werkzeug eingefuegter Dateiinhalt","synthetic":true}),
    );
    s.part(
        "prt_synth0003",
        "msg_synth0001",
        SESSION,
        json!({"type":"file","mime":"text/plain","filename":"notiz.txt"}),
    );

    s.message(
        "msg_synth0002",
        SESSION,
        1767323047000,
        assistant_data(1767323047000, a),
    );
    s.part(
        "prt_synth0004",
        "msg_synth0002",
        SESSION,
        json!({"type":"step-start"}),
    );
    s.part(
        "prt_synth0005",
        "msg_synth0002",
        SESSION,
        json!({"type":"reasoning","text":"Interne Ueberlegung, nicht importieren"}),
    );
    s.part(
        "prt_synth0006",
        "msg_synth0002",
        SESSION,
        json!({"type":"tool","callID":"call_synth1","tool":"read",
            "state":{"status":"completed","input":{"filePath":"/x"},
            "output":"Werkzeugausgabe, nicht importieren"}}),
    );
    s.part(
        "prt_synth0007",
        "msg_synth0002",
        SESSION,
        text("Die Testkatze heisst Minka."),
    );
    s.part(
        "prt_synth0008",
        "msg_synth0002",
        SESSION,
        json!({"type":"step-finish","reason":"stop"}),
    );

    s.message(
        "msg_synth0003",
        SESSION,
        1767323100000,
        user_data(1767323100000, b),
    );
    s.part(
        "prt_synth0009",
        "msg_synth0003",
        SESSION,
        text("Und mit dem zweiten Modell?"),
    );
    s.part(
        "prt_synth0010",
        "msg_synth0003",
        SESSION,
        json!({"type":"text","text":"Verworfener Text","ignored":true}),
    );

    s.message(
        "msg_synth0004",
        SESSION,
        1767323101000,
        assistant_data(1767323101000, b),
    );
    s.part(
        "prt_synth0011",
        "msg_synth0004",
        SESSION,
        text("Erster Absatz."),
    );
    s.part(
        "prt_synth0012",
        "msg_synth0004",
        SESSION,
        json!({"type":"tool","callID":"call_synth2","tool":"bash",
            "state":{"status":"error","input":{"command":"true"},
            "error":"Fehlertext, nicht importieren"}}),
    );
    s.part(
        "prt_synth0013",
        "msg_synth0004",
        SESSION,
        text("Zweiter Absatz."),
    );

    s.message(
        "msg_synth0005",
        SESSION,
        1767323150000,
        user_data(1767323150000, b),
    );
    s.part(
        "prt_synth0014",
        "msg_synth0005",
        SESSION,
        json!({"type":"compaction","auto":true}),
    );

    let mut summary = assistant_data(1767323151000, b);
    summary["summary"] = json!(true);
    summary["mode"] = json!("compaction");
    s.message("msg_synth0006", SESSION, 1767323151000, summary);
    s.part(
        "prt_synth0015",
        "msg_synth0006",
        SESSION,
        text("Zusammenfassung der bisherigen Sitzung, nicht importieren"),
    );

    let mut failed = assistant_data(1767323165000, b);
    failed["time"] = json!({"created":1767323165000_i64});
    failed["error"] = json!({"name":"UnknownError","data":{"message":"Abbruch"}});
    s.message("msg_synth0007", SESSION, 1767323165000, failed);
}

fn example(path: &Path) {
    let s = Source::create(path);
    fill_example(&s);
    s.close();
}

fn import(store: &MemoryStore, scope: &str, path: &Path, session: Option<&str>) -> HistoryImport {
    store
        .import_opencode_snapshot(scope, path, session)
        .unwrap()
}

fn hits(store: &MemoryStore, query: &str, tool: Option<HistoryTool>) -> Vec<HistoryHit> {
    store.history_search_filtered("p", query, 20, tool).unwrap()
}

/// Alle gespeicherten Verlaufszeilen in Einfügereihenfolge.
fn rows(db: &Path) -> Vec<[Option<String>; 7]> {
    let c = Connection::open(db).unwrap();
    let mut stmt = c
        .prepare(
            "SELECT scope, tool, model, session_id, uuid, role || ':' || text, created_at
             FROM history_messages ORDER BY id",
        )
        .unwrap();
    stmt.query_map([], |r| {
        Ok([
            r.get(0)?,
            r.get(1)?,
            r.get(2)?,
            r.get(3)?,
            r.get(4)?,
            r.get(5)?,
            r.get(6)?,
        ])
    })
    .unwrap()
    .collect::<rusqlite::Result<_>>()
    .unwrap()
}

fn row(model: &str, id: &str, content: &str, at: &str) -> [Option<String>; 7] {
    [
        Some("p".into()),
        Some("opencode".into()),
        Some(model.into()),
        Some(SESSION.into()),
        Some(format!("opencode:{SESSION}:{id}")),
        Some(content.into()),
        Some(at.into()),
    ]
}

#[test]
fn imports_only_observed_text_with_scope_time_and_model() {
    let t = Temp::new();
    example(&t.source());
    let store = t.store();
    let report = import(&store, "p", &t.source(), None);
    assert_eq!(report.error, None);
    assert_eq!((report.added, report.tool.as_str()), (4, "opencode"));
    assert_eq!(
        rows(&t.db()),
        vec![
            row(
                "anbieter-a/modell-a",
                "msg_synth0001",
                "user:Wie heisst die Testkatze?",
                "2026-01-02T03:04:06.000Z"
            ),
            row(
                "anbieter-a/modell-a",
                "msg_synth0002",
                "assistant:Die Testkatze heisst Minka.",
                "2026-01-02T03:04:07.000Z"
            ),
            row(
                "anbieter-b/modell-b",
                "msg_synth0003",
                "user:Und mit dem zweiten Modell?",
                "2026-01-02T03:05:00.000Z"
            ),
            row(
                "anbieter-b/modell-b",
                "msg_synth0004",
                "assistant:Erster Absatz.\nZweiter Absatz.",
                "2026-01-02T03:05:01.000Z"
            ),
        ]
    );
}

#[test]
fn tool_data_reasoning_synthetic_system_and_summaries_are_not_imported() {
    let t = Temp::new();
    example(&t.source());
    let store = t.store();
    import(&store, "p", &t.source(), None);
    for word in [
        "Ueberlegung",
        "Werkzeugausgabe",
        "Fehlertext",
        "eingefuegter",
        "Verworfener",
        "Zusammenfassung",
        "Systemtext",
        "notiz",
        "Abbruch",
    ] {
        assert!(hits(&store, word, None).is_empty(), "{word} übernommen");
    }
}

#[test]
fn search_with_tool_filter_opencode_finds_the_message() {
    let t = Temp::new();
    example(&t.source());
    let store = t.store();
    import(&store, "p", &t.source(), None);
    let found = hits(&store, "Minka", Some(HistoryTool::OpenCode));
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].tool, "opencode");
    assert_eq!(found[0].model.as_deref(), Some("anbieter-a/modell-a"));
    assert_eq!(found[0].status, "unverified");
    assert!(hits(&store, "Minka", Some(HistoryTool::Codex)).is_empty());
    assert!(hits(&store, "Minka", Some(HistoryTool::ClaudeCode)).is_empty());
    assert!(
        store
            .history_search_filtered("anderer", "Minka", 5, None)
            .unwrap()
            .is_empty(),
        "nur im gewählten Bereich"
    );
}

#[test]
fn model_is_only_set_when_the_message_names_provider_and_model() {
    let t = Temp::new();
    let s = Source::create(&t.source());
    s.message("msg_a", SESSION, 1000, user_data(1000, None));
    s.part("prt_a", "msg_a", SESSION, text("Ohne Modell Birne"));
    let mut half = assistant_data(2000, None);
    half["modelID"] = json!("nur-modell");
    s.message("msg_b", SESSION, 2000, half);
    s.part("prt_b", "msg_b", SESSION, text("Halbes Modell Birne"));
    s.close();
    let store = t.store();
    assert_eq!(import(&store, "p", &t.source(), None).added, 2);
    assert!(
        hits(&store, "Birne", None)
            .iter()
            .all(|h| h.model.is_none())
    );
    assert_eq!(
        hits(&store, "Ohne", None)[0].created_at,
        "1970-01-01T00:00:01.000Z"
    );
}

#[test]
fn repeated_and_newer_snapshots_are_deduplicated() {
    let t = Temp::new();
    example(&t.source());
    let store = t.store();
    assert_eq!(import(&store, "p", &t.source(), None).added, 4);
    assert_eq!(import(&store, "p", &t.source(), None).added, 0);

    let newer = t.0.join("neuer.db");
    let s = Source::create(&newer);
    fill_example(&s);
    s.message(
        "msg_synth0008",
        SESSION,
        1767323200000,
        user_data(1767323200000, None),
    );
    s.part(
        "prt_synth0016",
        "msg_synth0008",
        SESSION,
        text("Noch eine Frage"),
    );
    s.close();
    assert_eq!(import(&store, "p", &newer, None).added, 1);
    assert_eq!(rows(&t.db()).len(), 5);
    assert_eq!(
        import(&store, "q", &newer, None).added,
        5,
        "eigener Bereich"
    );
}

#[test]
fn unfinished_assistant_message_follows_with_a_later_snapshot() {
    let t = Temp::new();
    let s = Source::create(&t.source());
    let mut open = assistant_data(5000, None);
    open["time"] = json!({"created":5000});
    s.message("msg_x", SESSION, 5000, open);
    s.part("prt_x", "msg_x", SESSION, text("Halb geschrieben"));
    s.close();
    let store = t.store();
    assert_eq!(import(&store, "p", &t.source(), None).added, 0);

    let later = t.0.join("spaeter.db");
    let s = Source::create(&later);
    s.message("msg_x", SESSION, 5000, assistant_data(5000, None));
    s.part(
        "prt_x",
        "msg_x",
        SESSION,
        text("Halb geschrieben und fertig"),
    );
    s.close();
    assert_eq!(import(&store, "p", &later, None).added, 1);
    assert_eq!(hits(&store, "fertig", None).len(), 1);
}

#[test]
fn session_filter_and_child_sessions() {
    let t = Temp::new();
    let s = Source::create(&t.source());
    fill_example(&s);
    s.session("ses_zwei", None);
    s.message("msg_z", "ses_zwei", 1000, user_data(1000, None));
    s.part("prt_z", "msg_z", "ses_zwei", text("Zweite Sitzung Kirsche"));
    s.session("ses_kind", Some(SESSION));
    s.message("msg_k", "ses_kind", 1000, user_data(1000, None));
    s.part(
        "prt_k",
        "msg_k",
        "ses_kind",
        text("Auftrag an Unteragent Kirsche"),
    );
    s.close();
    let store = t.store();
    assert_eq!(import(&store, "p", &t.source(), Some("ses_zwei")).added, 1);
    let found = hits(&store, "Kirsche", None);
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].session_id, "ses_zwei");
    assert_eq!(import(&store, "p", &t.source(), None).added, 4);
    assert_eq!(hits(&store, "Unteragent", None).len(), 0, "Kindsitzung");
    assert!(
        store
            .import_opencode_snapshot("p", &t.source(), Some(" "))
            .is_err()
    );
}

#[test]
fn source_stays_byte_identical_and_gets_no_sidecars() {
    let t = Temp::new();
    example(&t.source());
    assert!(sidecars(&t.source()).is_empty(), "Testquelle ohne Sidecars");
    let before = fs::read(t.source()).unwrap();
    assert_eq!((before[18], before[19]), (2, 2), "Quelle im WAL-Format");
    let store = t.store();
    import(&store, "p", &t.source(), None);
    import(&store, "p", &t.source(), Some(SESSION));
    assert_eq!(fs::read(t.source()).unwrap(), before);
    assert!(
        sidecars(&t.source()).is_empty(),
        "{:?}",
        sidecars(&t.source())
    );
}

#[test]
fn path_with_uri_characters_is_read() {
    let t = Temp::new();
    let odd = t.0.join("ordner mit %20 ? und #");
    fs::create_dir(&odd).unwrap();
    let source = odd.join("snap 1%?#.db");
    example(&source);
    let store = t.store();
    let report = import(&store, "p", &source, None);
    assert_eq!((report.added, report.error), (4, None));
    assert!(sidecars(&source).is_empty());
}

fn failed(store: &MemoryStore, path: &Path) -> String {
    let report = import(store, "p", path, None);
    assert_eq!(report.added, 0);
    report.error.expect("Fehler erwartet")
}

#[test]
fn active_wal_or_journal_is_rejected_before_opening() {
    let t = Temp::new();
    example(&t.source());
    let store = t.store();
    let wal = sidecar(&t.source(), "-wal");
    fs::write(&wal, b"").unwrap();
    assert_eq!(import(&store, "p", &t.source(), None).added, 4, "leere WAL");

    let other = t.0.join("aktiv.db");
    example(&other);
    let before = fs::read(&other).unwrap();
    fs::write(sidecar(&other, "-wal"), b"nicht leer").unwrap();
    let error = failed(&store, &other);
    assert!(error.contains("WAL"), "{error}");
    assert!(error.contains(".backup"), "{error}");
    fs::remove_file(sidecar(&other, "-wal")).unwrap();
    fs::write(sidecar(&other, "-journal"), b"").unwrap();
    assert!(failed(&store, &other).contains("Journal"));
    assert_eq!(fs::read(&other).unwrap(), before);
    assert!(!sidecar(&other, "-shm").exists());

    let status = store.history_status("p").unwrap();
    assert_eq!(status.failed, 1);
    assert_eq!(status.messages, 4);
}

#[test]
fn source_equal_to_target_is_rejected() {
    let t = Temp::new();
    let store = t.store();
    assert!(failed(&store, &t.db()).contains("V-Mind-Datenbank"));
    let indirect = t.0.join(".").join("v.db");
    assert!(failed(&store, &indirect).contains("V-Mind-Datenbank"));
    #[cfg(unix)]
    {
        let link = t.0.join("verweis.db");
        std::os::unix::fs::symlink(t.db(), &link).unwrap();
        assert!(failed(&store, &link).contains("V-Mind-Datenbank"));
        let hard = t.0.join("hart.db");
        fs::hard_link(t.db(), &hard).unwrap();
        assert!(failed(&store, &hard).contains("V-Mind-Datenbank"));
    }
    assert_eq!(rows(&t.db()).len(), 0);
}

#[test]
fn unknown_schema_is_rejected_and_nothing_is_imported() {
    let t = Temp::new();
    let store = t.store();
    let cases = [
        ("ohne-part.db", "DROP TABLE part", "Tabelle part"),
        (
            "ohne-data.db",
            "ALTER TABLE message DROP COLUMN data",
            "Spalte message.data",
        ),
        (
            "ohne-parent.db",
            "ALTER TABLE session DROP COLUMN parent_id",
            "Spalte session.parent_id",
        ),
    ];
    for (name, change, expected) in cases {
        let path = t.0.join(name);
        let s = Source::create(&path);
        fill_example(&s);
        s.0.execute_batch(change).unwrap();
        s.close();
        let error = failed(&store, &path);
        assert!(error.contains(expected), "{error}");
    }
    let broken = t.0.join("kaputt.db");
    let s = Source::create(&broken);
    fill_example(&s);
    s.0.execute(
        "UPDATE part SET data='{kein json' WHERE id='prt_synth0001'",
        [],
    )
    .unwrap();
    s.close();
    assert!(failed(&store, &broken).contains("prt_synth0001"));
    let not_sqlite = t.0.join("text.db");
    fs::write(&not_sqlite, b"keine Datenbank").unwrap();
    assert!(!failed(&store, &not_sqlite).is_empty());
    assert!(!failed(&store, &t.0.join("fehlt.db")).is_empty());
    assert_eq!(rows(&t.db()).len(), 0);
}

#[test]
fn unknown_role_is_an_error() {
    let t = Temp::new();
    let s = Source::create(&t.source());
    s.message("msg_s", SESSION, 1000, json!({"role":"system"}));
    s.part("prt_s", "msg_s", SESSION, text("Systemrolle"));
    s.close();
    let store = t.store();
    assert!(failed(&store, &t.source()).contains("msg_s"));
}

#[test]
fn secrets_are_redacted_before_storing() {
    let t = Temp::new();
    let s = Source::create(&t.source());
    s.message("msg_g", SESSION, 1000, user_data(1000, None));
    // Zusammengesetzt, damit kein tokenförmiger Text im Quellcode steht.
    let body = "a1B2".repeat(9);
    let secret = format!("Schluessel gh{}_{body}", "p");
    s.part("prt_g", "msg_g", SESSION, text(&secret));
    s.close();
    let store = t.store();
    assert_eq!(import(&store, "p", &t.source(), None).added, 1);
    let stored = &rows(&t.db())[0][5];
    assert!(!stored.as_deref().unwrap().contains(&body), "{stored:?}");
}

#[test]
fn invalid_scope_is_rejected() {
    let t = Temp::new();
    example(&t.source());
    let store = t.store();
    assert!(
        store
            .import_opencode_snapshot(" ", &t.source(), None)
            .is_err()
    );
}

fn schema_eight(path: &Path) {
    let c = Connection::open(path).unwrap();
    for sql in [
        include_str!("../../../migrations/0001_memory.sql"),
        include_str!("../../../migrations/0002_retrieval.sql"),
        include_str!("../../../migrations/0003_project_context.sql"),
        include_str!("../../../migrations/0004_checks.sql"),
        include_str!("../../../migrations/0005_partial_search.sql"),
        include_str!("../../../migrations/0006_observations.sql"),
        include_str!("../../../migrations/0007_history.sql"),
        include_str!("../../../migrations/0008_history_origin.sql"),
    ] {
        c.execute_batch(sql).unwrap();
    }
    c.pragma_update(None, "user_version", 8).unwrap();
    c.execute(
        "INSERT INTO history_messages(id,scope,tool,model,session_id,uuid,role,text,created_at)
         VALUES(77,'p','codex','m','s','codex:s:item:1','user','Holunder aus Codex',
         '2026-01-01T00:00:00Z')",
        [],
    )
    .unwrap();
    c.execute(
        "INSERT INTO history_imports(scope,tool,source_path,byte_offset,last_error,unkeyed_lines,
         session_id,last_turn_id,last_model)
         VALUES('p','codex','/alt.jsonl',55,'Warnung: 1 beschädigte Zeile(n) übersprungen, letzte ab Byte 9',
         2,'s','t','m')",
        [],
    )
    .unwrap();
}

#[test]
fn migration_eight_to_nine_keeps_rows_search_and_state_and_backs_up() {
    let t = Temp::new();
    schema_eight(&t.db());
    assert!(
        MemoryStore::open_current(t.db()).is_err(),
        "kein Hook-Upgrade"
    );
    let store = MemoryStore::open_existing(t.db()).unwrap();
    assert_eq!(store.stats("global").unwrap().schema_version, 9);
    let old = hits(&store, "Holunder", Some(HistoryTool::Codex));
    assert_eq!(old.len(), 1);
    assert_eq!((old[0].id, old[0].model.as_deref()), (77, Some("m")));
    let source = &store.history_status("p").unwrap().sources[0];
    assert_eq!(
        (
            source.tool.as_str(),
            source.byte_offset,
            source.unkeyed_lines
        ),
        ("codex", 55, 2)
    );
    assert_eq!(source.corrupt_lines, 1);

    example(&t.source());
    assert_eq!(
        import(&store, "p", &t.source(), None).added,
        4,
        "Trigger aktiv"
    );
    assert_eq!(
        hits(&store, "Testkatze", Some(HistoryTool::OpenCode)).len(),
        2
    );
    let report = vmind_core::inspect_database(t.db()).unwrap();
    assert!(report.healthy, "{:?}", report.missing_objects);
    assert!(vmind_core::audit_secrets(t.db()).is_ok());
    let snapshots: Vec<_> = fs::read_dir(&t.0)
        .unwrap()
        .map(|e| e.unwrap().path())
        .filter(|p| p.to_string_lossy().contains("before-schema-9"))
        .collect();
    assert_eq!(snapshots.len(), 1);
    assert_eq!(
        vmind_core::inspect_database(&snapshots[0])
            .unwrap()
            .schema_version,
        8
    );
}
