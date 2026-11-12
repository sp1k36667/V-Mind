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
    fs::write(t.file(), "[1,2]\n").unwrap();
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
fn migration_six_to_current_keeps_data_and_writes_a_verified_backup() {
    let t = Temp::new();
    schema_six(&t.db());
    assert!(
        MemoryStore::open_current(t.db()).is_err(),
        "kein Hook-Upgrade"
    );
    let store = MemoryStore::open_existing(t.db()).unwrap();
    assert_eq!(store.stats("global").unwrap().schema_version, 8);
    assert_eq!(store.get(1).unwrap().unwrap().problem, "alt");
    assert_eq!(store.resume("p", None).unwrap().decisions[0].body, "bleibt");
    write(&t.file(), &[row("user", "u1", json!("nach Migration"))]);
    assert_eq!(import(&store, &t.file()).added, 1);
    let report = vmind_core::inspect_database(t.db()).unwrap();
    assert!(report.healthy, "{:?}", report.missing_objects);
    let snapshots: Vec<_> = fs::read_dir(&t.0)
        .unwrap()
        .map(|e| e.unwrap().path())
        .filter(|p| p.to_string_lossy().contains("before-schema-8"))
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

fn queued(uuid: &str, mode: &str, kind: &str, prompt: Value) -> Value {
    json!({"type":"attachment","uuid":uuid,"sessionId":"sitzung-1","isSidechain":false,
        "timestamp":"2026-01-01T00:00:00.000Z",
        "attachment":{"type":"queued_command","commandMode":mode,
            "origin":{"kind":kind},"prompt":prompt}})
}

#[test]
fn queued_user_commands_are_imported_once_as_user_messages() {
    let t = Temp::new();
    let store = t.store();
    let token = format!("gh{}_{}", "p", "a1B2".repeat(9));
    write(
        &t.file(),
        &[
            queued("q1", "prompt", "human", json!("Zwischenfrage Kolibri")),
            queued("q2", "prompt", "human", json!(format!("Kolibri {token}"))),
        ],
    );
    assert_eq!(import(&store, &t.file()).added, 2);
    assert_eq!(import(&store, &t.file()).added, 0);
    let other = t.0.join("kopie.jsonl");
    fs::copy(t.file(), &other).unwrap();
    assert_eq!(import(&store, &other).added, 0, "gleiche uuid im Bereich");
    let hits = store.history_search("p", "Kolibri", 20).unwrap();
    assert_eq!(hits.len(), 2);
    assert!(hits.iter().all(|h| h.role == "user"));
    let found = texts(&store, "p", "Kolibri");
    assert!(found.iter().any(|f| f == "Zwischenfrage Kolibri"));
    assert!(found.iter().all(|f| !f.contains(&token)));
    assert_eq!(messages(&store), 2);
}

#[test]
fn queued_notifications_and_other_attachments_are_not_user_text() {
    let t = Temp::new();
    let store = t.store();
    let mut meta = queued("n3", "prompt", "human", json!("Meldung Fremdtext"));
    meta["attachment"]["isMeta"] = json!(true);
    let mut sidechain = queued("n4", "prompt", "human", json!("Meldung Fremdtext"));
    sidechain["isSidechain"] = json!(true);
    let mut without_origin = queued("n6", "prompt", "human", json!("Meldung Fremdtext"));
    without_origin["attachment"]
        .as_object_mut()
        .unwrap()
        .remove("origin");
    write(
        &t.file(),
        &[
            queued(
                "n1",
                "task-notification",
                "task-notification",
                json!("<task-notification>Meldung Fremdtext</task-notification>"),
            ),
            queued("n2", "prompt", "peer", json!("Meldung Fremdtext")),
            meta,
            sidechain,
            queued(
                "n5",
                "task-notification",
                "human",
                json!("Meldung Fremdtext"),
            ),
            without_origin,
            json!({"type":"attachment","uuid":"n7","sessionId":"s","timestamp":"t",
                "attachment":{"type":"file","prompt":"Meldung Fremdtext"}}),
            json!({"type":"attachment","attachment":"Meldung Fremdtext"}),
        ],
    );
    let report = import(&store, &t.file());
    assert_eq!(report.error, None);
    assert_eq!(report.added, 0);
    assert!(texts(&store, "p", "Fremdtext").is_empty());
}

#[test]
fn a_human_queued_command_with_unexpected_structure_is_reported() {
    let t = Temp::new();
    let store = t.store();
    write(&t.file(), &[queued("q1", "prompt", "human", json!(7))]);
    let report = import(&store, &t.file());
    assert!(report.error.is_some());
    assert_eq!(report.offset, 0);
}

const OPEN: &str = "<system-reminder>";
const CLOSE: &str = "</system-reminder>";
/// Steht nur innerhalb synthetischer Systemblöcke und darf nirgends gespeichert werden.
const BLOCK_WORD: &str = "BLOCKINHALT";

fn block() -> String {
    format!("{OPEN}\n{BLOCK_WORD} vom System\n{CLOSE}")
}

fn db_contains(path: &Path, needle: &str) -> bool {
    fs::read(path)
        .unwrap()
        .windows(needle.len())
        .any(|w| w == needle.as_bytes())
}

/// Importiert eine Zeile und prüft gespeicherten Text, Suche und Datenbank-Bytes.
fn assert_cleaned(source: Value, query: &str, expected: &str) {
    let t = Temp::new();
    let store = t.store();
    write(&t.file(), &[source]);
    let report = import(&store, &t.file());
    assert_eq!(report.error, None);
    assert_eq!(report.added, 1);
    assert_eq!(texts(&store, "p", query), [expected]);
    assert!(
        texts(&store, "p", BLOCK_WORD).is_empty(),
        "Suche findet ihn"
    );
    drop(store);
    assert!(!db_contains(&t.db(), BLOCK_WORD), "steht in der Datenbank");
}

/// Ohne verbleibenden Text: keine Nachricht, kein Fehler, und der Stand schreitet fort.
fn assert_dropped(source: Value) {
    let t = Temp::new();
    let store = t.store();
    write(
        &t.file(),
        &[source, row("user", "nachher", json!("Folgezeile bleibt"))],
    );
    let report = import(&store, &t.file());
    assert_eq!(report.error, None);
    assert_eq!(report.added, 1);
    assert_eq!(report.offset, fs::metadata(t.file()).unwrap().len());
    assert_eq!(messages(&store), 1);
    assert_eq!(texts(&store, "p", "Folgezeile"), ["Folgezeile bleibt"]);
    assert!(texts(&store, "p", BLOCK_WORD).is_empty());
    drop(store);
    assert!(!db_contains(&t.db(), BLOCK_WORD), "steht in der Datenbank");
}

#[test]
fn leading_system_block_is_removed_and_user_text_kept() {
    let text = format!("{}\n\n  Echte Frage\n  zur Lampe  \n", block());
    assert_cleaned(
        row("user", "u1", json!(text)),
        "Lampe",
        "Echte Frage\n  zur Lampe",
    );
}

#[test]
fn leading_system_block_is_removed_from_text_block_lists() {
    let content = json!([
        {"type":"text","text":block()},
        {"type":"text","text":"Frage aus Liste"}
    ]);
    assert_cleaned(row("user", "u1", content), "Liste", "Frage aus Liste");
}

#[test]
fn message_with_only_a_system_block_is_not_stored_and_the_import_goes_on() {
    assert_dropped(row("user", "u1", json!(format!(" \n{}\n ", block()))));
}

#[test]
fn several_system_blocks_are_all_removed() {
    let text = format!("{0}Eins{0}Zwei Tulpe{0}", block());
    assert_cleaned(row("user", "u1", json!(text)), "Tulpe", "EinsZwei Tulpe");
}

#[test]
fn system_block_inside_the_text_leaves_both_sides_unchanged() {
    let text = format!("Vorher  Rose\n{}\nNachher", block());
    assert_cleaned(
        row("user", "u1", json!(text)),
        "Rose",
        "Vorher  Rose\n\nNachher",
    );
}

#[test]
fn opening_tag_without_end_drops_everything_from_the_tag_on() {
    let text = format!("Davor Birke {OPEN}{BLOCK_WORD} ohne Ende");
    assert_cleaned(row("user", "u1", json!(text)), "Birke", "Davor Birke");
}

#[test]
fn opening_tag_without_end_after_a_complete_block_keeps_the_text_between() {
    let text = format!("{}Mitte Eiche {OPEN}{BLOCK_WORD}", block());
    assert_cleaned(row("user", "u1", json!(text)), "Eiche", "Mitte Eiche");
}

#[test]
fn nested_system_tags_do_not_end_the_outer_block() {
    let text = format!("Davor Birke {OPEN}außen {} {BLOCK_WORD}", block());
    assert_cleaned(row("user", "u1", json!(text)), "Birke", "Davor Birke");

    let text = format!(
        "Davor Birke {OPEN}außen {} {BLOCK_WORD}{CLOSE} danach",
        block()
    );
    assert_cleaned(
        row("user", "u2", json!(text)),
        "Birke",
        "Davor Birke  danach",
    );
}

#[test]
fn closing_tag_without_start_drops_the_text_before_it() {
    let text = format!("{BLOCK_WORD} Rest{CLOSE}\nDanach Linde");
    assert_cleaned(row("user", "u1", json!(text)), "Linde", "Danach Linde");
}

#[test]
fn lone_broken_tags_leave_no_message() {
    assert_dropped(row("user", "u1", json!(format!("{OPEN}{BLOCK_WORD}"))));
    assert_dropped(row("user", "u1", json!(format!("{BLOCK_WORD}{CLOSE}"))));
}

#[test]
fn queued_commands_are_cleaned_like_user_messages() {
    let text = format!("{}\nZwischenfrage Ahorn", block());
    assert_cleaned(
        queued("q1", "prompt", "human", json!(text)),
        "Ahorn",
        "Zwischenfrage Ahorn",
    );
    assert_dropped(queued("q2", "prompt", "human", json!(block())));
}

#[test]
fn assistant_text_keeps_system_block_tags_unchanged() {
    let t = Temp::new();
    let store = t.store();
    let text = format!("Antwort Fichte {OPEN}zitiert{CLOSE} Ende {OPEN}offen");
    write(&t.file(), &[row("assistant", "a1", json!(text))]);
    assert_eq!(import(&store, &t.file()).added, 1);
    assert_eq!(texts(&store, "p", "Fichte"), [text]);
}

#[test]
fn mentioning_system_reminder_without_a_tag_stays_unchanged() {
    let text = "  Was bedeutet system-reminder oder /system-reminder> hier?  ";
    let t = Temp::new();
    let store = t.store();
    write(&t.file(), &[row("user", "u1", json!(text))]);
    assert_eq!(import(&store, &t.file()).added, 1);
    assert_eq!(texts(&store, "p", "bedeutet"), [text]);
}

/// Steht nur in synthetischen beschädigten Zeilen und darf nirgends gespeichert werden.
const CORRUPT_WORD: &str = "DEFEKTINHALT";

fn corrupt_line() -> String {
    format!("{{\"type\":\"user\",\"text\":\"{CORRUPT_WORD}\n")
}

/// Gültig, beschädigt, gültig; liefert die Byte-Position der beschädigten Zeile.
fn write_with_corrupt_line(path: &Path) -> u64 {
    let first = line(&row("user", "u1", json!("vor Schaden")));
    fs::write(
        path,
        format!(
            "{first}{}{}",
            corrupt_line(),
            line(&row("user", "u2", json!("nach Schaden")))
        ),
    )
    .unwrap();
    first.len() as u64
}

#[test]
fn corrupt_line_is_skipped_and_reported_with_both_valid_lines_imported() {
    let t = Temp::new();
    let store = t.store();
    let position = write_with_corrupt_line(&t.file());
    let report = import(&store, &t.file());
    assert_eq!(report.error, None);
    assert_eq!(report.added, 2);
    assert_eq!(report.offset, fs::metadata(t.file()).unwrap().len());
    assert_eq!(report.corrupt_lines, 1);
    let status = store.history_status("p").unwrap();
    assert_eq!(status.messages, 2);
    assert_eq!(status.failed, 0, "eine Warnung ist kein Fehler");
    let source = &status.sources[0];
    assert_eq!(source.last_error, None);
    assert_eq!(source.corrupt_lines, 1);
    let warning = source.warning.as_deref().expect("Warnung gespeichert");
    assert!(warning.contains(&format!("Byte {position}")), "{warning}");
}

#[test]
fn repeated_import_without_new_data_keeps_count_offset_and_warning() {
    let t = Temp::new();
    let store = t.store();
    write_with_corrupt_line(&t.file());
    let first = import(&store, &t.file());
    let before = store.history_status("p").unwrap().sources.remove(0);
    let second = import(&store, &t.file());
    assert_eq!(second.added, 0);
    assert_eq!(second.offset, first.offset);
    assert_eq!(second.corrupt_lines, 1);
    assert_eq!(second.warning, first.warning);
    let after = store.history_status("p").unwrap().sources.remove(0);
    assert_eq!(after.corrupt_lines, 1);
    assert_eq!(after.byte_offset, before.byte_offset);
    assert_eq!(after.warning, before.warning);
}

#[test]
fn appending_after_a_corrupt_line_imports_and_counts_only_new_damage() {
    let t = Temp::new();
    let store = t.store();
    write_with_corrupt_line(&t.file());
    let first = import(&store, &t.file());
    append(&t.file(), &line(&row("user", "u3", json!("angehängt"))));
    let second = import(&store, &t.file());
    assert_eq!(second.added, 1);
    assert_eq!(second.corrupt_lines, 1);
    assert_eq!(second.warning, first.warning);
    append(&t.file(), &corrupt_line());
    let third = import(&store, &t.file());
    assert_eq!(third.corrupt_lines, 2);
    let warning = third.warning.expect("Warnung");
    assert!(
        warning.contains(&format!("Byte {}", second.offset)),
        "letzte Position: {warning}"
    );
}

#[test]
fn a_replaced_shorter_file_does_not_count_old_damage_again() {
    let t = Temp::new();
    let store = t.store();
    write_with_corrupt_line(&t.file());
    assert_eq!(import(&store, &t.file()).corrupt_lines, 1);
    fs::write(t.file(), corrupt_line()).unwrap();
    let report = import(&store, &t.file());
    assert!(report.restarted);
    assert_eq!(report.corrupt_lines, 1, "neu gelesen, nicht addiert");
    fs::write(t.file(), "").unwrap();
    let report = import(&store, &t.file());
    assert!(report.restarted);
    assert_eq!(report.corrupt_lines, 0);
    assert_eq!(report.warning, None);
}

#[test]
fn a_later_error_keeps_the_warning_and_recovery_keeps_it_too() {
    let t = Temp::new();
    let store = t.store();
    write_with_corrupt_line(&t.file());
    let warning = import(&store, &t.file()).warning;
    append(&t.file(), "[1,2]\n");
    let stopped = import(&store, &t.file());
    assert!(stopped.error.is_some());
    assert_eq!(stopped.corrupt_lines, 1);
    assert_eq!(stopped.warning, warning);
    let status = store.history_status("p").unwrap();
    assert_eq!(status.failed, 1);
    assert_eq!(status.sources[0].corrupt_lines, 1);
    assert!(status.sources[0].last_error.is_some());
    let full = fs::read(t.file()).unwrap();
    fs::write(t.file(), &full[..full.len() - "[1,2]\n".len()]).unwrap();
    append(&t.file(), &line(&row("user", "u4", json!("repariert"))));
    let recovered = import(&store, &t.file());
    assert_eq!(recovered.error, None);
    assert_eq!(recovered.warning, warning);
    assert_eq!(store.history_status("p").unwrap().failed, 0);
}

#[test]
fn corrupt_line_found_before_a_stop_is_counted_once_after_the_retry() {
    let t = Temp::new();
    let store = t.store();
    fs::write(t.file(), format!("{}[1,2]\n", corrupt_line())).unwrap();
    for _ in 0..2 {
        let report = import(&store, &t.file());
        assert!(report.error.is_some());
        assert_eq!(report.corrupt_lines, 0, "Stopp übernimmt nichts");
        assert_eq!(report.offset, 0);
    }
    fs::write(t.file(), format!("{}{{}}\n", corrupt_line())).unwrap();
    assert!(import(&store, &t.file()).error.is_some(), "Zeile ohne Typ");
    let good = line(&row("user", "u1", json!("gut")));
    fs::write(t.file(), format!("{}{good}", corrupt_line())).unwrap();
    assert_eq!(import(&store, &t.file()).corrupt_lines, 1);
}

#[test]
fn incomplete_last_line_is_never_counted_as_corrupt() {
    let t = Temp::new();
    let store = t.store();
    write(&t.file(), &[row("user", "u1", json!("fertig"))]);
    let full = line(&row("user", "u2", json!("halb geschrieben")));
    let (head, tail) = full.split_at(full.len() / 2);
    append(&t.file(), head);
    let first = import(&store, &t.file());
    assert_eq!(first.corrupt_lines, 0);
    assert_eq!(first.warning, None);
    assert!(first.offset < fs::metadata(t.file()).unwrap().len());
    append(&t.file(), tail);
    let second = import(&store, &t.file());
    assert_eq!(second.added, 1);
    assert_eq!(second.corrupt_lines, 0);
    assert_eq!(texts(&store, "p", "halb").len(), 1);
}

#[test]
fn corrupt_line_content_never_reaches_the_database() {
    let t = Temp::new();
    let store = t.store();
    write_with_corrupt_line(&t.file());
    let report = import(&store, &t.file());
    assert!(!report.warning.unwrap().contains(CORRUPT_WORD));
    drop(store);
    assert!(!db_contains(&t.db(), CORRUPT_WORD), "Rohdaten gespeichert");
}

#[test]
fn invalid_utf8_counts_as_a_corrupt_line() {
    let t = Temp::new();
    let store = t.store();
    let mut bytes = b"\xff\xfe\n".to_vec();
    bytes.extend(line(&row("user", "u1", json!("danach"))).bytes());
    fs::write(t.file(), bytes).unwrap();
    let report = import(&store, &t.file());
    assert_eq!(report.added, 1);
    assert_eq!(report.corrupt_lines, 1);
}
