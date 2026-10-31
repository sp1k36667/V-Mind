use vmind_core::MemoryStore;

#[test]
fn only_validated_memories_are_retrieved() {
    let store = MemoryStore::in_memory().unwrap();
    let id = store
        .remember("error_solution", "Fehler", "Lösung", "Test")
        .unwrap();
    assert!(store.search("Fehler").unwrap().is_empty());
    assert!(
        store
            .validate(id, "Prüfer", "Reproduktion erfolgreich")
            .unwrap()
    );
    assert_eq!(store.search("Fehler").unwrap()[0].solution, "Lösung");
    assert!(!store.validate(id, "Prüfer", "erneut").unwrap());
    assert!(!store.validate(id + 1, "Prüfer", "Nachweis").unwrap());
}

#[test]
fn constraints_reject_invalid_data_and_validation() {
    let store = MemoryStore::in_memory().unwrap();
    for (kind, problem, solution, source) in [
        ("unknown", "a", "b", "c"),
        ("long_term", " ", "b", "c"),
        ("long_term", "a", "", "c"),
        ("long_term", "a", "b", ""),
    ] {
        assert!(store.remember(kind, problem, solution, source).is_err());
    }
    let id = store.remember("long_term", "a", "b", "c").unwrap();
    assert!(store.validate(id, "", "Nachweis").is_err());
    assert!(store.validate(id, "Prüfer", " ").is_err());
    assert!(store.search("a").unwrap().is_empty());
}

#[test]
fn literal_search_handles_sql_and_wildcards() {
    let store = MemoryStore::in_memory().unwrap();
    let text = "100% _ ' OR 1=1 --";
    let id = store.remember("long_term", text, "sicher", "Test").unwrap();
    store.validate(id, "Prüfer", "Test").unwrap();
    assert_eq!(store.search(text).unwrap().len(), 1);
    assert!(store.search("%").unwrap().len() == 1);
    assert!(store.search("unbekannt").unwrap().is_empty());
    assert!(store.search("").unwrap().is_empty());
}

#[test]
fn persists_across_reopening_and_migrates_once() {
    let path = std::env::temp_dir().join(format!(
        "vmind-{}-{}.db",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    {
        let store = MemoryStore::open(&path).unwrap();
        let id = store
            .remember("long_term", "Rust", "SQLite", "Test")
            .unwrap();
        store.validate(id, "Prüfer", "Test").unwrap();
    }
    {
        let store = MemoryStore::open(&path).unwrap();
        assert_eq!(store.search("Rust").unwrap().len(), 1);
    }
    std::fs::remove_file(path).unwrap();
}
