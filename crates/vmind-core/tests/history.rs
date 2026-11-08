//! Gesprächsverlauf: nur synthetische JSONL-Dateien, keine echten Transkripte.
use rusqlite::Connection;
use serde_json::{Value, json};
use std::{
    fs::{self, OpenOptions},
    io::Write,
    path::{Path, PathBuf},
};
use vmind_core::MemoryStore;

struct Temp(PathBuf);
impl Temp {
    fn new() -> Self {
        let p = std::env::temp_dir().join(format!(
            "vmind-history-{}-{}",
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
    fn file(&self) -> PathBuf {
        self.0.join("sitzung.jsonl")
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

fn row(kind: &str, uuid: &str, content: Value) -> Value {
    json!({"type":kind,"uuid":uuid,"sessionId":"sitzung-1",
        "timestamp":format!("2026-01-01T00:00:{:0>2}.000Z", uuid.len() % 60),
        "isSidechain":false,
        "message":{"role":kind,"content":content}})
}
fn line(value: &Value) -> String {
    format!("{value}\n")
}
fn write(path: &Path, rows: &[Value]) {
    fs::write(path, rows.iter().map(line).collect::<String>()).unwrap();
}
fn append(path: &Path, text: &str) {
    OpenOptions::new()
        .append(true)
        .open(path)
        .unwrap()
        .write_all(text.as_bytes())
        .unwrap();
}
fn texts(store: &MemoryStore, scope: &str, query: &str) -> Vec<String> {
    store
        .history_search(scope, query, 20)
        .unwrap()
        .into_iter()
        .map(|h| h.text)
        .collect()
}
fn import(store: &MemoryStore, path: &Path) -> vmind_core::HistoryImport {
    store.import_history_file("p", path, "ersatz").unwrap()
}
fn messages(store: &MemoryStore) -> i64 {
    store.history_status("p").unwrap().messages
}

#[test]
fn imports_only_user_and_assistant_text() {
    let t = Temp::new();
    let store = t.store();
    write(
        &t.file(),
        &[
            row("user", "u1", json!("Frage zur Glasbrücke")),
            row(
                "assistant",
                "a1",
                json!([
                    {"type":"thinking","thinking":"GEDANKE-DARF-NICHT","signature":"SIGNATUR-DARF-NICHT"},
                    {"type":"tool_use","id":"t1","name":"Bash","input":{"command":"WERKZEUG-DARF-NICHT"}},
                    {"type":"text","text":"Antwort zur Glasbrücke"}
                ]),
            ),
            row(
                "user",
                "u2",
                json!([{"type":"tool_result","tool_use_id":"t1","content":"ERGEBNIS-DARF-NICHT"}]),
            ),
            json!({"type":"system","content":"SYSTEM-DARF-NICHT","uuid":"s1"}),
            json!({"type":"attachment","attachment":"ANHANG-DARF-NICHT","uuid":"z1"}),
            json!({"type":"queue-operation","content":"WARTESCHLANGE-DARF-NICHT"}),
        ],
    );
    let report = import(&store, &t.file());
    assert_eq!(report.added, 2);
    assert_eq!(report.error, None);
    let mut found = texts(&store, "p", "Glasbrücke");
    found.sort();
    assert_eq!(found, ["Antwort zur Glasbrücke", "Frage zur Glasbrücke"]);
    drop(store);
    let bytes = fs::read(t.db()).unwrap();
    for forbidden in [
        "GEDANKE-DARF-NICHT",
        "SIGNATUR-DARF-NICHT",
        "WERKZEUG-DARF-NICHT",
        "ERGEBNIS-DARF-NICHT",
        "SYSTEM-DARF-NICHT",
        "ANHANG-DARF-NICHT",
        "WARTESCHLANGE-DARF-NICHT",
    ] {
        assert!(
            !bytes
                .windows(forbidden.len())
                .any(|w| w == forbidden.as_bytes()),
            "{forbidden} steht in der Datenbank"
        );
    }
}

#[test]
fn meta_sidechain_summary_and_api_error_lines_are_skipped() {
    let t = Temp::new();
    let store = t.store();
    let flagged = |flag: &str, uuid: &str| {
        let mut value = row("user", uuid, json!("Geheimtipp Sonderzeile"));
        value[flag] = json!(true);
        value
    };
    write(
        &t.file(),
        &[
            flagged("isMeta", "m1"),
            flagged("isSidechain", "m2"),
            flagged("isCompactSummary", "m3"),
            flagged("isVisibleInTranscriptOnly", "m4"),
            flagged("isApiErrorMessage", "m5"),
            row("user", "n1", json!("Geheimtipp Normalzeile")),
        ],
    );
    assert_eq!(import(&store, &t.file()).added, 1);
    assert_eq!(texts(&store, "p", "Geheimtipp"), ["Geheimtipp Normalzeile"]);
}

#[test]
fn repeated_import_adds_no_duplicates_even_after_a_restart_from_zero() {
    let t = Temp::new();
    let store = t.store();
    write(&t.file(), &[row("user", "u1", json!("einmalig Eintrag"))]);
    assert_eq!(import(&store, &t.file()).added, 1);
    assert_eq!(import(&store, &t.file()).added, 0);
    let other = t.0.join("kopie.jsonl");
    fs::copy(t.file(), &other).unwrap();
    assert_eq!(import(&store, &other).added, 0, "gleiche uuid im Bereich");
    assert_eq!(messages(&store), 1);
    assert_eq!(texts(&store, "p", "einmalig").len(), 1);
}

#[test]
fn only_appended_lines_are_read_on_the_next_run() {
    let t = Temp::new();
    let store = t.store();
    write(&t.file(), &[row("user", "u1", json!("erster Stand"))]);
    let first = import(&store, &t.file());
    append(
        &t.file(),
        &line(&row("assistant", "a2", json!("zweiter Stand"))),
    );
    let second = import(&store, &t.file());
    assert_eq!(second.added, 1);
    assert!(second.offset > first.offset);
    assert_eq!(second.offset, fs::metadata(t.file()).unwrap().len());
    assert!(!second.restarted);
}

#[test]
fn shorter_file_is_read_from_the_start_again() {
    let t = Temp::new();
    let store = t.store();
    write(
        &t.file(),
        &[
            row("user", "u1", json!("alt eins")),
            row("user", "u2", json!("alt zwei")),
        ],
    );
    import(&store, &t.file());
    write(&t.file(), &[row("user", "u3", json!("neu"))]);
    let report = import(&store, &t.file());
    assert!(report.restarted);
    assert_eq!(report.added, 1);
    assert_eq!(report.offset, fs::metadata(t.file()).unwrap().len());
    assert_eq!(messages(&store), 3);
}

#[test]
fn incomplete_last_line_waits_for_its_end() {
    let t = Temp::new();
    let store = t.store();
    write(&t.file(), &[row("user", "u1", json!("fertige Zeile"))]);
    let full = line(&row("assistant", "a2", json!("halbe Zeile folgt")));
    let (head, tail) = full.split_at(full.len() / 2);
    append(&t.file(), head);
    let first = import(&store, &t.file());
    assert_eq!(first.added, 1);
    assert_eq!(first.error, None, "unvollständig ist kein Fehler");
    append(&t.file(), tail);
    let second = import(&store, &t.file());
    assert_eq!(second.added, 1, "die halbe Zeile wurde nicht übersprungen");
    assert_eq!(second.offset, fs::metadata(t.file()).unwrap().len());
    assert_eq!(texts(&store, "p", "halbe").len(), 1);
}

fn assert_rejected(bad: &str) {
    let t = Temp::new();
    let store = t.store();
    fs::write(
        t.file(),
        format!(
            "{}{bad}\n{}",
            line(&row("user", "u1", json!("vor Fehler"))),
            line(&row("user", "u2", json!("nach Fehler")))
        ),
    )
    .unwrap();
    let report = import(&store, &t.file());
    let message = report.error.expect("Fehler gemeldet");
    assert!(!message.contains("INHALT"), "kein Zeileninhalt: {message}");
    assert_eq!(report.added, 0, "{bad}");
    assert_eq!(report.offset, 0, "nicht fortgeschrieben: {bad}");
    assert_eq!(messages(&store), 0, "{bad}");
    let status = store.history_status("p").unwrap();
    assert_eq!(status.failed, 1);
    assert_eq!(status.sources[0].byte_offset, 0);
    assert!(status.sources[0].last_error.is_some());
}

#[test]
fn unknown_structure_is_recorded_and_the_file_does_not_advance() {
    for bad in [
        "kein json INHALT",
        "[1,2]",
        r#"{"kein_typ":"INHALT"}"#,
        r#"{"type":"user","uuid":"x","sessionId":"s","timestamp":"t"}"#,
        r#"{"type":"user","sessionId":"s","timestamp":"t","message":{"role":"user","content":"INHALT"}}"#,
        r#"{"type":"user","uuid":"x","sessionId":"s","message":{"role":"user","content":"INHALT"}}"#,
        r#"{"type":"user","uuid":"x","sessionId":"s","timestamp":"t","message":{"role":"assistant","content":"INHALT"}}"#,
        r#"{"type":"user","uuid":"x","sessionId":"s","timestamp":"t","message":{"role":"user","content":7}}"#,
        r#"{"type":"user","uuid":"x","sessionId":"s","timestamp":"t","message":{"role":"user","content":[7]}}"#,
        r#"{"type":"user","uuid":"x","sessionId":"s","timestamp":"t","message":{"role":"user","content":[{"type":"text","text":7}]}}"#,
        r#"{"type":"user","uuid":"x","isMeta":"INHALT","sessionId":"s","timestamp":"t","message":{"role":"user","content":"x"}}"#,
    ] {
        assert_rejected(bad);
    }
}

#[test]
fn a_successful_import_clears_a_previous_error() {
    let t = Temp::new();
    let store = t.store();
    fs::write(t.file(), "kein json\n").unwrap();
    assert!(import(&store, &t.file()).error.is_some());
    write(&t.file(), &[row("user", "u1", json!("wieder gut"))]);
    let report = import(&store, &t.file());
    assert_eq!(report.error, None);
    assert_eq!(store.history_status("p").unwrap().failed, 0);
}

#[test]
fn missing_file_and_directory_are_recorded_without_advancing() {
    let t = Temp::new();
    let store = t.store();
    assert!(import(&store, &t.0.join("fehlt.jsonl")).error.is_some());
    assert!(import(&store, &t.0).error.is_some());
    assert_eq!(store.history_status("p").unwrap().failed, 2);
}

#[test]
fn known_secret_formats_are_replaced_before_storing() {
    let t = Temp::new();
    let store = t.store();
    let token = format!("gh{}_{}", "p", "a1B2".repeat(9));
    let text = format!("Schlüssel {token} benutzt");
    write(&t.file(), &[row("user", "u1", json!(text))]);
    import(&store, &t.file());
    let found = texts(&store, "p", "Schlüssel");
    assert_eq!(found.len(), 1);
    assert_eq!(found[0], "Schlüssel [REDIGIERT GitHub-Token] benutzt");
    let audit_clean = vmind_core::audit_secrets(t.db()).unwrap();
    assert!(audit_clean.findings.is_empty());
    drop(store);
    let bytes = fs::read(t.db()).unwrap();
    assert!(!bytes.windows(token.len()).any(|w| w == token.as_bytes()));
}

#[test]
fn audit_covers_history_tables() {
    let t = Temp::new();
    let store = t.store();
    let token = format!("gh{}_{}", "p", "a1B2".repeat(9));
    store
        .record_history_error("p", &format!("/x/{token}.jsonl"), "Fehler")
        .unwrap();
    let report = vmind_core::audit_secrets(t.db()).unwrap();
    let tables: Vec<&str> = report.scanned.iter().map(|s| s.table).collect();
    assert!(tables.contains(&"history_messages"), "{tables:?}");
    assert!(tables.contains(&"history_imports"), "{tables:?}");
    assert_eq!(report.findings.len(), 1);
    assert_eq!(report.findings[0].table, "history_imports");
    assert_eq!(report.findings[0].field, "source_path");
}

#[test]
fn long_messages_are_cut_to_a_fixed_length_and_marked() {
    let t = Temp::new();
    let store = t.store();
    write(
        &t.file(),
        &[row(
            "user",
            "u1",
            json!(format!("Anfang {}", "ä".repeat(20_000))),
        )],
    );
    import(&store, &t.file());
    let found = texts(&store, "p", "Anfang");
    assert_eq!(found.len(), 1);
    assert!(found[0].chars().count() <= 8_020);
    assert!(found[0].ends_with("[gekürzt]"));
}

#[test]
fn missing_session_id_uses_the_fallback_and_hits_are_marked_unverified() {
    let t = Temp::new();
    let store = t.store();
    let mut value = row("assistant", "a1", json!([{"type":"text","text":"Zebra"}]));
    value.as_object_mut().unwrap().remove("sessionId");
    write(&t.file(), &[value]);
    import(&store, &t.file());
    let hit = store.history_search("p", "zebra", 5).unwrap().remove(0);
    assert_eq!(hit.session_id, "ersatz");
    assert_eq!(hit.role, "assistant");
    assert_eq!(hit.uuid, "a1");
    assert_eq!(hit.status, "unverified");
}

#[test]
fn search_is_limited_to_the_exact_scope() {
    let t = Temp::new();
    let store = t.store();
    write(
        &t.file(),
        &[row("user", "u1", json!("Bereichsgrenze hier"))],
    );
    store.import_history_file("p", &t.file(), "s").unwrap();
    store.import_history_file("q", &t.file(), "s").unwrap();
    let other = t.0.join("global.jsonl");
    write(&other, &[row("user", "g1", json!("Bereichsgrenze global"))]);
    store.import_history_file("global", &other, "s").unwrap();
    assert_eq!(texts(&store, "p", "Bereichsgrenze").len(), 1);
    assert_eq!(texts(&store, "q", "Bereichsgrenze").len(), 1);
    assert_eq!(
        texts(&store, "global", "Bereichsgrenze"),
        ["Bereichsgrenze global"]
    );
    assert!(texts(&store, "r", "Bereichsgrenze").is_empty());
}

#[test]
fn search_requires_all_words_ignores_fts_syntax_and_folds_accents() {
    let t = Temp::new();
    let store = t.store();
    write(
        &t.file(),
        &[
            row("user", "u1", json!("Rote Kaffeemaschine im Büro")),
            row("user", "u2", json!("Blaue Kaffeemaschine zuhause")),
        ],
    );
    import(&store, &t.file());
    assert_eq!(texts(&store, "p", "rote KAFFEEMASCHINE").len(), 1);
    assert_eq!(texts(&store, "p", "buro").len(), 1);
    assert_eq!(texts(&store, "p", "NEAR(\"x\" OR *").len(), 0);
    assert!(texts(&store, "p", "  -- ?! ").is_empty());
    let many = (0..400)
        .map(|n| format!("w{n}"))
        .collect::<Vec<_>>()
        .join(" ");
    assert!(texts(&store, "p", &many).is_empty(), "viele Begriffe");
}

#[test]
fn search_prefers_relevance_then_newest_and_checks_limits() {
    let t = Temp::new();
    let store = t.store();
    let at = |uuid: &str, stamp: &str| {
        let mut v = row("user", uuid, json!("gleicher Suchtext"));
        v["timestamp"] = json!(stamp);
        v
    };
    write(
        &t.file(),
        &[
            at("u1", "2026-01-01T00:00:00.000Z"),
            at("u2", "2026-03-01T00:00:00.000Z"),
            at("u3", "2026-02-01T00:00:00.000Z"),
        ],
    );
    import(&store, &t.file());
    let uuids: Vec<String> = store
        .history_search("p", "suchtext", 2)
        .unwrap()
        .into_iter()
        .map(|h| h.uuid)
        .collect();
    assert_eq!(uuids, ["u2", "u3"]);
    for limit in [0, 21] {
        assert!(store.history_search("p", "x", limit).is_err());
    }
    assert!(store.history_search("p", &"a".repeat(2001), 5).is_err());
    assert!(store.history_search(" ", "x", 5).is_err());
}

#[test]
fn history_stays_out_of_recall_resume_and_journal_search() {
    let t = Temp::new();
    let store = t.store();
    write(
        &t.file(),
        &[row("user", "u1", json!("Verlaufswort Papagei"))],
    );
    import(&store, &t.file());
    assert!(
        store
            .recall_with_hints("Papagei", "p", 20)
            .unwrap()
            .is_empty()
    );
    assert!(store.journal_search("p", "Papagei", 20).unwrap().is_empty());
    let resume = serde_json::to_string(&store.resume("p", None).unwrap()).unwrap();
    assert!(!resume.contains("Papagei"));
    assert_eq!(texts(&store, "p", "Papagei").len(), 1);
}

fn schema_six(path: &Path) {
    let c = Connection::open(path).unwrap();
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
    c.execute(
        "INSERT INTO memories(kind,problem,solution,source) VALUES('long_term','alt','bewahren','Test')",
        [],
    )
    .unwrap();
    c.execute(
        "INSERT INTO project_journal(scope,kind,body,source) VALUES('p','decision','bleibt','Test')",
        [],
    )
    .unwrap();
}

#[test]
fn migration_six_to_seven_keeps_data_and_writes_a_verified_backup() {
    let t = Temp::new();
    schema_six(&t.db());
    assert!(
        MemoryStore::open_current(t.db()).is_err(),
        "kein Hook-Upgrade"
    );
    let store = MemoryStore::open_existing(t.db()).unwrap();
    assert_eq!(store.stats("global").unwrap().schema_version, 7);
    assert_eq!(store.get(1).unwrap().unwrap().problem, "alt");
    assert_eq!(store.resume("p", None).unwrap().decisions[0].body, "bleibt");
    write(&t.file(), &[row("user", "u1", json!("nach Migration"))]);
    assert_eq!(import(&store, &t.file()).added, 1);
    let report = vmind_core::inspect_database(t.db()).unwrap();
    assert!(report.healthy, "{:?}", report.missing_objects);
    let snapshots: Vec<_> = fs::read_dir(&t.0)
        .unwrap()
        .map(|e| e.unwrap().path())
        .filter(|p| p.to_string_lossy().contains("before-schema-7"))
        .collect();
    assert_eq!(snapshots.len(), 1);
    let old = vmind_core::inspect_database(&snapshots[0]).unwrap();
    assert!(old.healthy);
    assert_eq!(old.schema_version, 6);
}

#[test]
fn doctor_reports_a_missing_history_index() {
    let t = Temp::new();
    drop(t.store());
    Connection::open(t.db())
        .unwrap()
        .execute_batch("DROP TRIGGER history_fts_insert")
        .unwrap();
    let report = vmind_core::inspect_database(t.db()).unwrap();
    assert!(!report.healthy);
    assert_eq!(report.missing_objects, ["history_fts_insert"]);
}
