//! Codex-Verlaufsimport und Herkunft (ab Schema 8): nur synthetische JSONL-Dateien.
use rusqlite::Connection;
use serde_json::{Value, json};
use std::{
    fs::{self, OpenOptions},
    io::Write,
    path::{Path, PathBuf},
};
use vmind_core::{HistoryHit, HistoryImport, HistoryTool, MemoryStore};

const SESSION: &str = "00000000-0000-7000-8000-00000000000a";
const STAMP: &str = "2026-01-02T03:04:05.000Z";
const FIXTURE: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/tests/fixtures/codex-rollout-synthetisch.jsonl"
);

struct Temp(PathBuf);
impl Temp {
    fn new() -> Self {
        let p = std::env::temp_dir().join(format!(
            "vmind-codex-{}-{}",
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
        self.0.join("rollout.jsonl")
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

fn meta() -> Value {
    json!({"timestamp":STAMP,"ordinal":0,"type":"session_meta","payload":{"id":SESSION}})
}
fn context(turn: &str, model: &str) -> Value {
    json!({"timestamp":STAMP,"type":"turn_context","payload":{"turn_id":turn,"model":model}})
}
fn completed(turn: &str, item: Value) -> Value {
    json!({"timestamp":STAMP,"ordinal":100,"type":"event_msg",
        "payload":{"type":"item_completed","turn_id":turn,"item":item}})
}
fn user(id: &str, text: &str) -> Value {
    completed(
        "t1",
        json!({"type":"UserMessage","id":id,"client_id":"c",
            "content":[{"type":"text","text":text,"text_elements":[]}]}),
    )
}
fn agent(id: &str, phase: &str, text: &str) -> Value {
    completed(
        "t1",
        json!({"type":"AgentMessage","id":id,"phase":phase,
            "content":[{"type":"Text","text":text}]}),
    )
}
fn claude(uuid: &str, text: &str) -> Value {
    json!({"type":"user","uuid":uuid,"sessionId":"sitzung-c","timestamp":STAMP,
        "message":{"role":"user","content":text}})
}
fn line(value: &Value) -> String {
    format!("{value}\n")
}
fn write(path: &Path, rows: &[Value]) {
    fs::write(path, rows.iter().map(line).collect::<String>()).unwrap();
}
fn append(path: &Path, rows: &[Value]) {
    OpenOptions::new()
        .append(true)
        .open(path)
        .unwrap()
        .write_all(rows.iter().map(line).collect::<String>().as_bytes())
        .unwrap();
}
fn import(store: &MemoryStore, path: &Path) -> HistoryImport {
    store.import_codex_history_file("p", path).unwrap()
}
fn hits(store: &MemoryStore, query: &str) -> Vec<HistoryHit> {
    store.history_search("p", query, 20).unwrap()
}
fn uuid(key: &str) -> String {
    format!("codex:{SESSION}:{key}")
}
fn db_contains(path: &Path, needle: &str) -> bool {
    fs::read(path)
        .unwrap()
        .windows(needle.len())
        .any(|w| w == needle.as_bytes())
}
fn one_message(item: Value) -> usize {
    let t = Temp::new();
    let store = t.store();
    write(&t.file(), &[meta(), completed("t1", item)]);
    let report = import(&store, &t.file());
    assert_eq!(report.error, None);
    report.added
}

#[test]
fn synthetic_rollout_imports_exactly_the_real_conversation() {
    let t = Temp::new();
    let store = t.store();
    let report = store
        .import_codex_history_file("p", Path::new(FIXTURE))
        .unwrap();
    assert_eq!(report.error, None);
    assert_eq!(report.added, 6);
    assert_eq!(report.corrupt_lines, 1);
    assert_eq!(report.unkeyed_lines, 0, "ohne client_id zählt nicht");
    assert!(report.offset < fs::metadata(FIXTURE).unwrap().len());
    let session = "00000000-0000-7000-8000-000000000001";
    let mut found: Vec<(String, String, Option<String>, String)> = Connection::open(t.db())
        .unwrap()
        .prepare("SELECT uuid, role, model, tool FROM history_messages ORDER BY id")
        .unwrap()
        .query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)))
        .unwrap()
        .collect::<Result<_, _>>()
        .unwrap();
    let model = Some("modell-beispiel-1".to_owned());
    let expected: Vec<_> = [
        ("item:u-1", "user"),
        ("item:a-2", "assistant"),
        ("item:u-3", "user"),
        ("item:u-4", "user"),
        ("ordinal:25", "user"),
        ("item:a-4", "assistant"),
    ]
    .into_iter()
    .map(|(key, role)| {
        (
            format!("codex:{session}:{key}"),
            role.to_owned(),
            model.clone(),
            "codex".to_owned(),
        )
    })
    .collect();
    assert_eq!(found.len(), expected.len());
    found.iter_mut().zip(&expected).for_each(|(a, b)| {
        assert_eq!(a, b);
    });
    drop(store);
    for forbidden in [
        "ERFUNDEN-NICHT-IMPORTIEREN",
        "/erfunden/bild.png",
        "Automatisch eingereihte",
        "Ich schaue kurz",
        "Soll ich fortfahren",
    ] {
        assert!(!db_contains(&t.db(), forbidden), "{forbidden}");
    }
}

#[test]
fn appended_lines_keep_session_and_model_and_a_repeat_adds_nothing() {
    let t = Temp::new();
    let store = t.store();
    write(
        &t.file(),
        &[meta(), context("t1", "m-1"), user("u1", "Frage Apfel")],
    );
    let first = import(&store, &t.file());
    assert_eq!(first.added, 1);
    append(&t.file(), &[agent("a1", "final_answer", "Antwort Apfel")]);
    let second = import(&store, &t.file());
    assert_eq!(second.added, 1);
    assert!(second.offset > first.offset);
    assert_eq!(import(&store, &t.file()).added, 0);
    let found = hits(&store, "Apfel");
    assert_eq!(found.len(), 2);
    assert!(found.iter().all(|h| h.session_id == SESSION));
    assert!(found.iter().all(|h| h.model.as_deref() == Some("m-1")));
}

#[test]
fn response_items_are_ignored_so_nothing_is_stored_twice() {
    let t = Temp::new();
    let store = t.store();
    let duplicate = json!({"timestamp":STAMP,"type":"response_item","payload":{
        "type":"message","id":"a1","role":"assistant",
        "content":[{"type":"output_text","text":"Birne doppelt"}]}});
    let only_there = json!({"timestamp":STAMP,"type":"response_item","payload":{
        "type":"message","id":"a9","role":"assistant",
        "content":[{"type":"output_text","text":"Birne nur Antwortstrom"}]}});
    write(
        &t.file(),
        &[
            meta(),
            agent("a1", "final_answer", "Birne doppelt"),
            duplicate,
            only_there,
        ],
    );
    assert_eq!(import(&store, &t.file()).added, 1);
    assert_eq!(hits(&store, "Birne").len(), 1);
}

#[test]
fn ordinal_is_a_separate_fallback_only_when_the_id_is_missing() {
    let t = Temp::new();
    let store = t.store();
    let without_id = |ordinal: i64| {
        let mut value = completed(
            "t1",
            json!({"type":"UserMessage","client_id":"c",
                "content":[{"type":"text","text":"Kirsche ohne Kennung"}]}),
        );
        value["ordinal"] = json!(ordinal);
        value
    };
    write(
        &t.file(),
        &[
            meta(),
            without_id(7),
            without_id(8),
            user("ordinal:7", "Kirsche mit passender Kennung"),
        ],
    );
    assert_eq!(import(&store, &t.file()).added, 3);
    let mut keys: Vec<String> = hits(&store, "Kirsche")
        .into_iter()
        .map(|h| h.uuid)
        .collect();
    keys.sort();
    assert_eq!(
        keys,
        [uuid("item:ordinal:7"), uuid("ordinal:7"), uuid("ordinal:8")]
    );
}

#[test]
fn messages_without_any_key_are_skipped_and_reported_without_raw_text() {
    let t = Temp::new();
    let store = t.store();
    let mut unkeyed = completed(
        "t1",
        json!({"type":"UserMessage","client_id":"c",
            "content":[{"type":"text","text":"ROHTEXT-OHNE-SCHLUESSEL"}]}),
    );
    unkeyed.as_object_mut().unwrap().remove("ordinal");
    write(&t.file(), &[meta(), unkeyed, user("u1", "Daneben gut")]);
    let report = import(&store, &t.file());
    assert_eq!(report.error, None);
    assert_eq!(report.added, 1);
    assert_eq!(report.unkeyed_lines, 1);
    assert_eq!(report.offset, fs::metadata(t.file()).unwrap().len());
    let status = store.history_status("p").unwrap();
    assert_eq!((status.failed, status.warned), (0, 1));
    assert_eq!(status.sources[0].unkeyed_lines, 1);
    assert_eq!(import(&store, &t.file()).unkeyed_lines, 1, "nicht doppelt");
    let shown = serde_json::to_string(&status).unwrap();
    assert!(!shown.contains("ROHTEXT"), "{shown}");
    drop(store);
    assert!(!db_contains(&t.db(), "ROHTEXT-OHNE-SCHLUESSEL"));
}

#[test]
fn scope_is_strict() {
    let t = Temp::new();
    let store = t.store();
    write(&t.file(), &[meta(), user("u1", "Dattel im Bereich")]);
    assert_eq!(import(&store, &t.file()).added, 1);
    assert_eq!(
        store
            .import_codex_history_file("q", &t.file())
            .unwrap()
            .added,
        1,
        "gleiche ID in anderem Bereich"
    );
    assert_eq!(hits(&store, "Dattel").len(), 1);
    assert!(store.history_search("r", "Dattel", 5).unwrap().is_empty());
    assert!(
        store
            .history_search("global", "Dattel", 5)
            .unwrap()
            .is_empty()
    );
    assert!(store.import_codex_history_file(" ", &t.file()).is_err());
}

#[test]
fn same_id_and_same_path_do_not_collide_between_tools() {
    let t = Temp::new();
    let store = t.store();
    let shared = uuid("item:u1");
    write(
        &t.file(),
        &[
            meta(),
            user("u1", "Feige von Codex"),
            claude(&shared, "Feige von Claude"),
        ],
    );
    assert_eq!(import(&store, &t.file()).added, 1);
    let claude_run = store.import_history_file("p", &t.file(), "x").unwrap();
    assert_eq!(claude_run.added, 1, "Stand je Werkzeug getrennt");
    assert_eq!(claude_run.error, None);
    let found = hits(&store, "Feige");
    assert_eq!(found.len(), 2);
    assert!(found.iter().all(|h| h.uuid == shared));
    let status = store.history_status("p").unwrap();
    let mut tools: Vec<&str> = status.sources.iter().map(|s| s.tool.as_str()).collect();
    tools.sort();
    assert_eq!(tools, ["claude-code", "codex"]);
    assert_eq!(import(&store, &t.file()).added, 0);
}

#[test]
fn equal_texts_with_different_ids_are_all_kept() {
    let t = Temp::new();
    let store = t.store();
    write(
        &t.file(),
        &[
            meta(),
            user("u1", "Gleiche Guave"),
            user("u2", "Gleiche Guave"),
        ],
    );
    assert_eq!(import(&store, &t.file()).added, 2);
    assert_eq!(hits(&store, "Guave").len(), 2);
}

#[test]
fn user_messages_need_a_non_empty_client_id_but_may_start_with_a_bracket() {
    let message = |client: Option<Value>| {
        let mut item = json!({"type":"UserMessage","id":"u1",
            "content":[{"type":"text","text":"<b>Hallo</b> Holunder"}]});
        if let Some(client) = client {
            item["client_id"] = client;
        }
        item
    };
    assert_eq!(one_message(message(None)), 0);
    assert_eq!(one_message(message(Some(Value::Null))), 0);
    assert_eq!(one_message(message(Some(json!("  ")))), 0);
    assert_eq!(one_message(message(Some(json!("c")))), 1);
}

/// Importiert genau eine Nutzernachricht und liefert den gespeicherten Text, falls einer bleibt.
fn stored_user_text(text: &str) -> (Temp, Option<String>) {
    let t = Temp::new();
    let store = t.store();
    write(&t.file(), &[meta(), user("u1", text)]);
    let report = import(&store, &t.file());
    assert_eq!(report.error, None);
    let stored = Connection::open(t.db())
        .unwrap()
        .query_row("SELECT text FROM history_messages", [], |r| r.get(0))
        .ok();
    (t, stored)
}

/// Prüft gespeicherten Text, Suchindex und Datenbank-Bytes einer bereinigten Nachricht.
fn assert_envelope_removed(text: &str, expected: &str, inner: &[&str]) {
    let (t, stored) = stored_user_text(text);
    assert_eq!(stored.as_deref(), Some(expected), "{text}");
    let store = t.store();
    assert_eq!(hits(&store, "Nutzerfrage").len(), 1, "{text}");
    for word in inner {
        assert!(hits(&store, word).is_empty(), "Suchindex findet {word}");
    }
    drop(store);
    for word in inner {
        assert!(!db_contains(&t.db(), word), "{word} gespeichert");
    }
}

#[test]
fn nested_app_context_is_removed_as_one_outer_block() {
    let text =
        "Nutzerfrage <app-context><app-context>innen</app-context>internerprobe</app-context> Ende";
    assert_envelope_removed(text, "Nutzerfrage  Ende", &["innen", "internerprobe"]);
    let (t, _) = stored_user_text(text);
    assert_eq!(hits(&t.store(), "Ende").len(), 1);
}

#[test]
fn browser_context_with_attributes_is_removed() {
    assert_envelope_removed(
        "Nutzerfrage <in-app-browser-context source=\"seite\">browserinhalt</in-app-browser-context> Ende",
        "Nutzerfrage  Ende",
        &["browserinhalt", "seite"],
    );
    assert_envelope_removed(
        "Nutzerfrage <in-app-browser-context source=\"a\"><app-context>gemischt</app-context>restinhalt</in-app-browser-context> Ende",
        "Nutzerfrage  Ende",
        &["gemischt", "restinhalt"],
    );
}

#[test]
fn unterminated_envelope_drops_everything_from_its_tag_on() {
    assert_envelope_removed(
        "Nutzerfrage Ende <app-context>offeninhalt ohne Abschluss",
        "Nutzerfrage Ende",
        &["offeninhalt"],
    );
    assert_envelope_removed(
        "Nutzerfrage Ende <app-context><app-context>tiefinhalt</app-context>halbinhalt",
        "Nutzerfrage Ende",
        &["tiefinhalt", "halbinhalt"],
    );
    assert_envelope_removed(
        "Nutzerfrage Ende <in-app-browser-context source=\"kaputtinhalt",
        "Nutzerfrage Ende",
        &["kaputtinhalt"],
    );
}

#[test]
fn an_envelope_alone_leaves_no_message() {
    let (_t, stored) = stored_user_text("<app-context>nurhuelle</app-context>");
    assert_eq!(stored, None);
}

#[test]
fn unknown_tags_similar_names_and_plain_text_stay() {
    for text in [
        "<eigenes>Ingwer bleibt</eigenes>",
        "Was ist <environment_context> Ingwer?",
        "Ingwer <app-contextual>bleibt</app-contextual>",
        "Ingwer mit </app-context> ohne Anfang",
        "  Ingwer mit Rand  ",
    ] {
        let (_t, stored) = stored_user_text(text);
        assert_eq!(stored.as_deref(), Some(text));
    }
}

#[test]
fn only_synchronous_final_answers_with_capital_text_blocks_are_taken() {
    let message = |phase: Value, delivery: Option<&str>, block: &str| {
        let mut item = json!({"type":"AgentMessage","id":"a1","phase":phase,
            "content":[{"type":block,"text":"Johannisbeere"}]});
        if let Some(delivery) = delivery {
            item["delivery"] = json!(delivery);
        }
        item
    };
    assert_eq!(one_message(message(json!("final_answer"), None, "Text")), 1);
    assert_eq!(
        one_message(message(json!("final_answer"), Some("sync"), "Text")),
        1
    );
    assert_eq!(one_message(message(json!("commentary"), None, "Text")), 0);
    assert_eq!(
        one_message(message(json!("final_answer"), Some("async"), "Text")),
        0
    );
    assert_eq!(one_message(message(json!("final_answer"), None, "text")), 0);
    assert_eq!(one_message(message(Value::Null, None, "Text")), 0);
}

#[test]
fn model_is_only_assigned_through_the_same_turn_id() {
    let t = Temp::new();
    let store = t.store();
    let in_turn = |id: &str, turn: &str| {
        completed(
            turn,
            json!({"type":"AgentMessage","id":id,"phase":"final_answer",
                "content":[{"type":"Text","text":format!("Kiwi {id}")}]}),
        )
    };
    let mut no_turn = in_turn("a-ohne", "x");
    no_turn["payload"]
        .as_object_mut()
        .unwrap()
        .remove("turn_id");
    write(
        &t.file(),
        &[
            meta(),
            context("t1", "m-1"),
            in_turn("a-passend", "t1"),
            in_turn("a-fremd", "t2"),
            no_turn,
            context("t3", "m-3"),
            context("t3", "m-anders"),
            in_turn("a-widerspruch", "t3"),
            in_turn("a-spaet", "t4"),
            context("t4", "m-4"),
        ],
    );
    assert_eq!(import(&store, &t.file()).added, 5);
    let model = |key: &str| {
        hits(&store, &format!("Kiwi {key}"))
            .into_iter()
            .find(|h| h.uuid == uuid(&format!("item:{key}")))
            .unwrap()
            .model
    };
    assert_eq!(model("a-passend").as_deref(), Some("m-1"));
    assert_eq!(model("a-fremd"), None);
    assert_eq!(model("a-ohne"), None);
    assert_eq!(model("a-widerspruch"), None);
    assert_eq!(model("a-spaet").as_deref(), Some("m-4"));
}

#[test]
fn unknown_relevant_structure_stops_without_advancing() {
    let bad_item = |item: Value| completed("t1", item).to_string();
    for bad in [
        "[1,2]".to_owned(),
        r#"{"kein_typ":"INHALT"}"#.to_owned(),
        r#"{"type":"event_msg","payload":{"text":"INHALT"}}"#.to_owned(),
        bad_item(json!({"text":"INHALT"})),
        bad_item(json!({"type":"UserMessage","id":"x","client_id":"c","content":"INHALT"})),
        bad_item(json!({"type":"UserMessage","id":"x","client_id":"c","content":[7]})),
        bad_item(json!({"type":"UserMessage","id":"x","client_id":"c",
            "content":[{"type":"text","text":7}]})),
        bad_item(json!({"type":"UserMessage","id":"x","client_id":7,
            "content":[{"type":"text","text":"INHALT"}]})),
        bad_item(json!({"type":"AgentMessage","id":"x","phase":7,
            "content":[{"type":"Text","text":"INHALT"}]})),
        bad_item(json!({"type":"UserMessage","id":7,"client_id":"c",
            "content":[{"type":"text","text":"INHALT"}]})),
        json!({"timestamp":STAMP,"type":"session_meta","payload":{"id":"andere-sitzung"}})
            .to_string(),
    ] {
        let t = Temp::new();
        let store = t.store();
        fs::write(t.file(), format!("{}{}\n", line(&meta()), bad)).unwrap();
        let report = import(&store, &t.file());
        let message = report.error.expect("Fehler gemeldet");
        assert!(!message.contains("INHALT"), "{message}");
        assert_eq!(report.offset, 0, "{bad}");
        assert_eq!(report.added, 0, "{bad}");
        assert_eq!(store.history_status("p").unwrap().failed, 1, "{bad}");
    }
}

#[test]
fn a_message_before_any_session_meta_stops_the_file() {
    let t = Temp::new();
    let store = t.store();
    write(&t.file(), &[user("u1", "Limette")]);
    let report = import(&store, &t.file());
    assert!(report.error.is_some());
    assert_eq!(report.offset, 0);
    assert_eq!(store.history_status("p").unwrap().messages, 0);
}

#[test]
fn a_composed_key_over_the_limit_stops_instead_of_failing_in_sqlite() {
    let t = Temp::new();
    let store = t.store();
    write(&t.file(), &[meta(), user(&"x".repeat(190), "Mango")]);
    let report = import(&store, &t.file());
    assert!(report.error.is_some());
    assert_eq!(report.offset, 0);
}

#[test]
fn corrupt_lines_are_counted_and_a_shorter_file_starts_over() {
    let t = Temp::new();
    let store = t.store();
    fs::write(
        t.file(),
        format!(
            "{}{{\"kaputt\n{}",
            line(&meta()),
            line(&user("u1", "Nektarine"))
        ),
    )
    .unwrap();
    let first = import(&store, &t.file());
    assert_eq!((first.added, first.corrupt_lines), (1, 1));
    assert_eq!(import(&store, &t.file()).corrupt_lines, 1);
    write(&t.file(), &[meta()]);
    let again = import(&store, &t.file());
    assert!(again.restarted);
    assert_eq!(again.corrupt_lines, 0);
}

#[test]
fn a_restart_does_not_reuse_the_old_session() {
    let t = Temp::new();
    let store = t.store();
    write(
        &t.file(),
        &[meta(), user("u1", "Olive eins"), user("u2", "Olive zwei")],
    );
    import(&store, &t.file());
    write(&t.file(), &[user("u3", "Olive")]);
    let report = import(&store, &t.file());
    assert!(
        report.error.is_some(),
        "session_meta fehlt nach Neuschreiben"
    );
}

#[test]
fn search_can_be_filtered_by_tool_and_stays_compatible_without_a_filter() {
    let t = Temp::new();
    let store = t.store();
    write(&t.file(), &[meta(), user("u1", "Papaya Codex")]);
    import(&store, &t.file());
    let other = t.0.join("claude.jsonl");
    write(&other, &[claude("c1", "Papaya Claude")]);
    store.import_history_file("p", &other, "x").unwrap();
    assert_eq!(hits(&store, "Papaya").len(), 2);
    let only = |tool| {
        store
            .history_search_filtered("p", "Papaya", 20, Some(tool))
            .unwrap()
    };
    let codex = only(HistoryTool::Codex);
    assert_eq!(codex.len(), 1);
    assert_eq!(codex[0].tool, "codex");
    assert_eq!(codex[0].status, "unverified");
    let claude_hits = only(HistoryTool::ClaudeCode);
    assert_eq!(claude_hits.len(), 1);
    assert_eq!(claude_hits[0].tool, "claude-code");
    assert!(HistoryTool::parse("hermes").is_err());
}

#[test]
fn claude_import_stays_as_it_was_and_takes_a_per_message_model() {
    let t = Temp::new();
    let store = t.store();
    let answer = |uuid: &str, model: Value| {
        json!({"type":"assistant","uuid":uuid,"sessionId":"s","timestamp":STAMP,
            "message":{"role":"assistant","model":model,
                "content":[{"type":"text","text":format!("Quitte {uuid}")}]}})
    };
    write(
        &t.file(),
        &[
            claude("u1", "Quitte Frage"),
            answer("a1", json!("claude-beispiel")),
            answer("a2", json!("<synthetic>")),
            answer("a3", json!(7)),
        ],
    );
    let report = store.import_history_file("p", &t.file(), "x").unwrap();
    assert_eq!(report.error, None);
    assert_eq!(report.added, 4);
    assert_eq!(report.tool, "claude-code");
    let model = |uuid: &str| {
        hits(&store, "Quitte")
            .into_iter()
            .find(|h| h.uuid == uuid)
            .unwrap()
            .model
    };
    assert_eq!(model("u1"), None);
    assert_eq!(model("a1").as_deref(), Some("claude-beispiel"));
    assert_eq!(model("a2"), None, "kein echtes Modell");
    assert_eq!(model("a3"), None, "unsicher bleibt leer");
    assert!(
        hits(&store, "Quitte")
            .iter()
            .all(|h| h.tool == "claude-code")
    );
}

fn schema_seven(path: &Path) {
    let c = Connection::open(path).unwrap();
    for sql in [
        include_str!("../../../migrations/0001_memory.sql"),
        include_str!("../../../migrations/0002_retrieval.sql"),
        include_str!("../../../migrations/0003_project_context.sql"),
        include_str!("../../../migrations/0004_checks.sql"),
        include_str!("../../../migrations/0005_partial_search.sql"),
        include_str!("../../../migrations/0006_observations.sql"),
        include_str!("../../../migrations/0007_history.sql"),
    ] {
        c.execute_batch(sql).unwrap();
    }
    c.pragma_update(None, "user_version", 7).unwrap();
    c.execute(
        "INSERT INTO history_messages(id,scope,session_id,uuid,role,text,created_at)
         VALUES(41,'p','s-alt','u-alt','user','Rhabarber vom Altbestand','2026-01-01T00:00:00Z')",
        [],
    )
    .unwrap();
    c.execute(
        "INSERT INTO history_imports(scope,source_path,byte_offset,last_error)
         VALUES('p','/alt.jsonl',123,'Warnung: 2 beschädigte Zeile(n) übersprungen, letzte ab Byte 99')",
        [],
    )
    .unwrap();
}

#[test]
fn migration_seven_to_current_keeps_ids_search_and_warnings_and_backs_up() {
    let t = Temp::new();
    schema_seven(&t.db());
    assert!(
        MemoryStore::open_current(t.db()).is_err(),
        "kein Hook-Upgrade"
    );
    let store = MemoryStore::open_existing(t.db()).unwrap();
    assert_eq!(store.stats("global").unwrap().schema_version, 9);

    let old = hits(&store, "Rhabarber");
    assert_eq!(old.len(), 1, "Suche nach der Migration");
    assert_eq!(old[0].id, 41);
    assert_eq!(old[0].uuid, "u-alt");
    assert_eq!(old[0].tool, "claude-code");
    assert_eq!(old[0].model, None);

    let status = store.history_status("p").unwrap();
    let source = &status.sources[0];
    assert_eq!(source.tool, "claude-code");
    assert_eq!(source.byte_offset, 123);
    assert_eq!(source.corrupt_lines, 2);
    assert!(source.warning.as_deref().unwrap().contains("Byte 99"));
    assert_eq!((status.failed, status.warned), (0, 1));

    write(&t.file(), &[meta(), user("u1", "Rhabarber neu")]);
    assert_eq!(import(&store, &t.file()).added, 1, "Trigger aktiv");
    assert_eq!(hits(&store, "Rhabarber").len(), 2);
    let report = vmind_core::inspect_database(t.db()).unwrap();
    assert!(report.healthy, "{:?}", report.missing_objects);
    assert!(vmind_core::audit_secrets(t.db()).is_ok());

    let snapshots: Vec<_> = fs::read_dir(&t.0)
        .unwrap()
        .map(|e| e.unwrap().path())
        .filter(|p| p.to_string_lossy().contains("before-schema-9"))
        .collect();
    assert_eq!(snapshots.len(), 1);
    let backup = vmind_core::inspect_database(&snapshots[0]).unwrap();
    assert!(backup.healthy);
    assert_eq!(backup.schema_version, 7);
}

#[test]
fn audit_still_reads_a_schema_seven_database() {
    let t = Temp::new();
    schema_seven(&t.db());
    assert!(vmind_core::audit_secrets(t.db()).is_ok());
}
