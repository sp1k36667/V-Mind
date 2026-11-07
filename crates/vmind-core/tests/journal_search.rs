use vmind_core::MemoryStore;

struct Temp(std::path::PathBuf);
impl Temp {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "vmind-journal-search-{}-{}",
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

fn note(s: &MemoryStore, scope: &str, body: &str, source: &str) -> i64 {
    s.journal(scope, "note", None, None, body, source).unwrap()
}
fn ids(found: &[vmind_core::JournalEntry]) -> Vec<i64> {
    found.iter().map(|e| e.id).collect()
}

#[test]
fn search_stays_in_the_exact_scope_without_global() {
    let s = MemoryStore::in_memory().unwrap();
    let own = note(&s, "p", "SQLite Migration geprüft", "Test");
    note(&s, "global", "SQLite Migration global", "Test");
    note(&s, "anderes", "SQLite Migration anderswo", "Test");
    let found = s.journal_search("p", "sqlite migration", 20).unwrap();
    assert_eq!(ids(&found), vec![own]);
    assert!(found.iter().all(|e| e.scope == "p"));
    let global = s.journal_search("global", "migration", 20).unwrap();
    assert!(global.iter().all(|e| e.scope == "global"));
    assert_eq!(global.len(), 1);
}

#[test]
fn every_word_must_match_somewhere() {
    let s = MemoryStore::in_memory().unwrap();
    let both = note(&s, "p", "Backup vor Migration erstellt", "Test");
    note(&s, "p", "Nur Backup", "Test");
    note(&s, "p", "Nur Migration", "Test");
    assert_eq!(
        ids(&s.journal_search("p", "backup migration", 20).unwrap()),
        vec![both]
    );
    // Wörter dürfen auf verschiedene Felder verteilt sein.
    let split = note(&s, "p", "Hook ergänzt", "hooks.rs Zeile 12");
    assert_eq!(
        ids(&s.journal_search("p", "hook zeile", 20).unwrap()),
        vec![split]
    );
}

#[test]
fn case_is_ignored_including_umlauts() {
    let s = MemoryStore::in_memory().unwrap();
    let id = note(&s, "p", "Änderung am Schema besprochen", "Test");
    assert_eq!(
        ids(&s.journal_search("p", "ÄNDERUNG", 20).unwrap()),
        vec![id]
    );
    assert_eq!(
        ids(&s.journal_search("p", "änderung SCHEMA", 20).unwrap()),
        vec![id]
    );
}

#[test]
fn accents_are_not_folded() {
    // Dokumentierte Grenze: é und e gelten als verschiedene Zeichen.
    let s = MemoryStore::in_memory().unwrap();
    let id = note(&s, "p", "Café-Test bestanden", "Test");
    assert!(s.journal_search("p", "cafe", 20).unwrap().is_empty());
    assert_eq!(ids(&s.journal_search("p", "CAFÉ", 20).unwrap()), vec![id]);
}

#[test]
fn partial_words_match() {
    let s = MemoryStore::in_memory().unwrap();
    let id = note(&s, "p", "Migration 0007 ergänzt", "Test");
    assert_eq!(ids(&s.journal_search("p", "Migra", 20).unwrap()), vec![id]);
}

#[test]
fn source_and_task_key_are_searched() {
    let s = MemoryStore::in_memory().unwrap();
    let by_source = note(&s, "p", "Prüfung bestanden", "cargo test --workspace");
    let by_key = s
        .journal(
            "p",
            "task",
            Some("tagebuchsuche"),
            Some("in_progress"),
            "Arbeit begonnen",
            "Auftrag",
        )
        .unwrap();
    assert_eq!(
        ids(&s.journal_search("p", "workspace", 20).unwrap()),
        vec![by_source]
    );
    assert_eq!(
        ids(&s.journal_search("p", "TAGEBUCH", 20).unwrap()),
        vec![by_key]
    );
}

#[test]
fn newest_first_and_limit_stops_early() {
    let s = MemoryStore::in_memory().unwrap();
    let a = note(&s, "p", "Treffer eins", "Test");
    note(&s, "p", "kein Fund", "Test");
    let b = note(&s, "p", "Treffer zwei", "Test");
    let c = note(&s, "p", "Treffer drei", "Test");
    assert_eq!(
        ids(&s.journal_search("p", "treffer", 20).unwrap()),
        vec![c, b, a]
    );
    assert_eq!(
        ids(&s.journal_search("p", "treffer", 2).unwrap()),
        vec![c, b]
    );
}

#[test]
fn query_without_words_returns_nothing() {
    let s = MemoryStore::in_memory().unwrap();
    note(&s, "p", "Eintrag", "Test");
    assert!(s.journal_search("p", "", 5).unwrap().is_empty());
    assert!(s.journal_search("p", "  -- ?! ", 5).unwrap().is_empty());
}

#[test]
fn invalid_input_is_rejected() {
    let s = MemoryStore::in_memory().unwrap();
    let long = "a".repeat(2001);
    assert!(s.journal_search("p", &long, 5).is_err());
    assert!(s.journal_search("p", &"a".repeat(2000), 5).is_ok());
    for limit in [0, 21] {
        let err = s.journal_search("p", "x", limit).unwrap_err();
        assert!(
            err.to_string().contains("Limit muss 1 bis 20 sein"),
            "{err}"
        );
    }
    assert!(s.journal_search(" ", "x", 5).is_err());
    assert!(s.journal_search(&"p".repeat(129), "x", 5).is_err());
}

#[test]
fn existing_file_database_is_searchable_after_reopen() {
    let temp = Temp::new();
    let path = temp.0.join("j.db");
    let (old, new) = {
        let s = MemoryStore::open(&path).unwrap();
        let old = note(&s, "p", "Bestandseintrag Migration", "Test");
        note(&s, "global", "Migration global", "Test");
        let new = note(&s, "p", "Neuere Migration", "Test");
        (old, new)
    };
    let s = MemoryStore::open(&path).unwrap();
    assert_eq!(
        ids(&s.journal_search("p", "migration", 5).unwrap()),
        vec![new, old]
    );
}
