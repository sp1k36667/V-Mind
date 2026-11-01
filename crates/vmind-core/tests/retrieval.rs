use rusqlite::Connection;
use vmind_core::MemoryStore;

struct TempDb(std::path::PathBuf);
impl TempDb {
    fn new() -> Self {
        Self(std::env::temp_dir().join(
            format!("vmind-v2-{}-{}.db",std::process::id(),
            std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()),
        ))
    }
}
impl Drop for TempDb {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}
fn add(store: &MemoryStore, scope: &str, problem: &str, solution: &str) -> i64 {
    let id = store
        .remember_scoped(scope, "error_solution", problem, solution, "Testquelle")
        .unwrap();
    store
        .validate(id, "Testprüfer", "Automatisierter Test")
        .unwrap();
    id
}

#[test]
fn scopes_prevent_cross_project_retrieval_and_include_global() {
    let s = MemoryStore::in_memory().unwrap();
    let global = add(&s, "global", "SQLite global", "Gemeinsam");
    let local = add(&s, "project-a", "SQLite lokal", "A");
    let other = add(&s, "project-b", "SQLite privat", "B");
    let ids: Vec<_> = s
        .recall("SQLITE", "project-a", 20)
        .unwrap()
        .iter()
        .map(|r| r.id)
        .collect();
    assert!(ids.contains(&global));
    assert!(ids.contains(&local));
    assert!(!ids.contains(&other));
    let global_only = s.recall("sqlite", "global", 20).unwrap();
    assert_eq!(global_only.len(), 1);
    assert_eq!(global_only[0].id, global);
}

#[test]
fn pending_and_invalidated_entries_are_excluded_with_history_preserved() {
    let s = MemoryStore::in_memory().unwrap();
    let pending = s
        .remember("long_term", "Migration", "Pending", "Quelle")
        .unwrap();
    let active = add(&s, "global", "Migration", "Validiert");
    assert_eq!(s.recall("Migration", "global", 5).unwrap().len(), 1);
    assert!(s.invalidate(active, "Reviewer", "Falsche Lösung").unwrap());
    assert!(!s.invalidate(active, "Reviewer", "Doppelt").unwrap());
    assert!(s.recall("Migration", "global", 5).unwrap().is_empty());
    assert!(s.search("Migration").unwrap().is_empty());
    assert_eq!(
        s.get(active)
            .unwrap()
            .unwrap()
            .invalidation_reason
            .as_deref(),
        Some("Falsche Lösung")
    );
    let events = s.history(active).unwrap();
    assert_eq!(
        events.iter().map(|e| e.action.as_str()).collect::<Vec<_>>(),
        ["created", "validated", "invalidated"]
    );
    assert_eq!(events[1].reason, "Automatisierter Test");
    assert_eq!(events[2].actor, "Reviewer");
    assert!(s.invalidate(pending, "Reviewer", "Unbrauchbar").unwrap());
    assert!(!s.validate(pending, "Reviewer", "Nicht zulässig").unwrap());
    assert!(s.pending("global").unwrap().is_empty());
    let stats = s.stats("global").unwrap();
    assert_eq!(stats.invalidated, 2);
    assert_eq!(stats.pending, 0);
    assert_eq!(stats.validated, 0);
}

#[test]
fn fulltext_handles_german_case_diacritics_and_user_syntax() {
    let s = MemoryStore::in_memory().unwrap();
    let id = add(
        &s,
        "global",
        "Fehler beim Öffnen",
        "Migration atomar durchführen",
    );
    let found = s
        .recall("Wie behebe ich FEHLER beim offnen?", "global", 5)
        .unwrap();
    assert_eq!(found[0].id, id);
    assert_eq!(found[0].source, "Testquelle");
    assert_eq!(found[0].validated_by.as_deref(), Some("Testprüfer"));
    assert!(
        s.recall("\" OR * NOT : ()", "global", 5)
            .unwrap()
            .is_empty()
    );
    assert!(s.recall("der die und", "global", 5).unwrap().is_empty());
    assert!(s.recall("sqlite", "global", 0).is_err());
    assert!(s.recall("sqlite", "global", 21).is_err());
    assert!(s.recall(&"x".repeat(2001), "global", 5).is_err());
}

#[test]
fn problem_matches_rank_above_solution_matches() {
    let s = MemoryStore::in_memory().unwrap();
    add(&s, "global", "Allgemeine Information", "SQLite");
    let focused = add(&s, "global", "SQLite", "Allgemeine Information");
    assert_eq!(s.recall("sqlite", "global", 1).unwrap()[0].id, focused);
}

#[test]
fn validates_limits_and_does_not_audit_failed_changes() {
    let s = MemoryStore::in_memory().unwrap();
    assert!(s.remember_scoped(" ", "long_term", "a", "b", "c").is_err());
    assert!(s.remember("long_term", "\u{2003}", "b", "c").is_err());
    assert!(
        s.remember("long_term", "a", &"x".repeat(16001), "c")
            .is_err()
    );
    let id = s.remember("long_term", "a", "b", "c").unwrap();
    assert!(s.validate(id, " ", "x").is_err());
    assert!(s.invalidate(id, "a", " ").is_err());
    assert!(!s.invalidate(999, "a", "x").unwrap());
    assert_eq!(s.history(id).unwrap().len(), 1);
    assert!(s.get(999).unwrap().is_none());
}

#[test]
fn migrates_v1_without_losing_data_and_rebuilds_fulltext() {
    let path = TempDb::new();
    {
        let c = Connection::open(&path.0).unwrap();
        c.execute_batch(include_str!("../../../migrations/0001_memory.sql"))
            .unwrap();
        c.execute_batch("PRAGMA user_version=1;
            INSERT INTO memories(kind,problem,solution,source,status,validated_by,evidence)
            VALUES('error_solution','SQLite Migration','Atomar','Alte Quelle','validated','Prüfer','Alter Nachweis');").unwrap();
    }
    for _ in 0..2 {
        let s = MemoryStore::open(&path.0).unwrap();
        let records = s.recall("SQLite", "global", 5).unwrap();
        assert_eq!(records.len(), 1);
        assert_eq!(records[0].evidence.as_deref(), Some("Alter Nachweis"));
        assert_eq!(s.history(1).unwrap().len(), 1);
        assert_eq!(s.history(1).unwrap()[0].action, "imported");
        assert_eq!(s.stats("global").unwrap().schema_version, 6);
    }
}

#[test]
fn failed_migration_rolls_back_and_future_versions_remain_untouched() {
    let path = TempDb::new();
    {
        let c = Connection::open(&path.0).unwrap();
        c.execute_batch(include_str!("../../../migrations/0001_memory.sql"))
            .unwrap();
        c.execute_batch("PRAGMA user_version=1; CREATE TABLE memory_events(dummy TEXT);")
            .unwrap();
    }
    assert!(MemoryStore::open(&path.0).is_err());
    let c = Connection::open(&path.0).unwrap();
    let columns: i64 = c
        .query_row(
            "SELECT count(*) FROM pragma_table_info('memories') WHERE name='scope'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(columns, 0);
    let version: i64 = c
        .query_row("PRAGMA user_version", [], |r| r.get(0))
        .unwrap();
    assert_eq!(version, 1);
    c.execute_batch("PRAGMA user_version=99;").unwrap();
    assert!(MemoryStore::open(&path.0).is_err());
    let version: i64 = c
        .query_row("PRAGMA user_version", [], |r| r.get(0))
        .unwrap();
    assert_eq!(version, 99);
}

#[test]
fn independent_connections_observe_validation_and_withdrawal() {
    let path = TempDb::new();
    let first = MemoryStore::open(&path.0).unwrap();
    let second = MemoryStore::open(&path.0).unwrap();
    let id = first
        .remember("long_term", "Nebenläufigkeit", "SQLite", "Quelle")
        .unwrap();
    assert!(
        second
            .recall("Nebenläufigkeit", "global", 5)
            .unwrap()
            .is_empty()
    );
    assert!(second.validate(id, "Tester", "Test").unwrap());
    assert_eq!(
        first.recall("Nebenläufigkeit", "global", 5).unwrap().len(),
        1
    );
    first
        .invalidate(id, "Tester", "Testweise zurückgezogen")
        .unwrap();
    assert!(
        second
            .recall("Nebenläufigkeit", "global", 5)
            .unwrap()
            .is_empty()
    );
}

#[test]
fn validated_lists_only_active_entries_of_scope_and_global_newest_first() {
    let s = MemoryStore::in_memory().unwrap();
    let global = add(&s, "global", "Global", "G");
    let own = add(&s, "p", "Eigen", "E");
    add(&s, "anderes", "Fremd", "F");
    s.remember_scoped("p", "long_term", "Ungeprüft", "U", "Testquelle")
        .unwrap();
    let withdrawn = add(&s, "p", "Zurückgezogen", "Z");
    s.invalidate(withdrawn, "Testprüfer", "veraltet").unwrap();
    let ids: Vec<_> = s.validated("p", 10).unwrap().iter().map(|r| r.id).collect();
    assert_eq!(ids, [own, global]);
    assert_eq!(s.validated("p", 1).unwrap()[0].id, own);
    assert!(s.validated("p", 0).is_err());
    assert!(s.validated(" ", 10).is_err());
}
