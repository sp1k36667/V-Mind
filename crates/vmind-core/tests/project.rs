use vmind_core::MemoryStore;
struct Temp(std::path::PathBuf);
impl Temp {
    fn new() -> Self {
        Self(std::env::temp_dir().join(format!(
                "vmind-project-{}-{}.db",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            )))
    }
}
impl Drop for Temp {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}
#[test]
fn restart_restores_goal_tasks_decisions_and_last_answer() {
    let path = Temp::new();
    let session;
    {
        let s = MemoryStore::open(&path.0).unwrap();
        session = s.default_conversation("a").unwrap();
        s.journal("a", "goal", None, None, "V-Mind bauen", "Nutzer")
            .unwrap();
        s.journal(
            "a",
            "task",
            Some("sqlite"),
            Some("in_progress"),
            "Migration implementieren",
            "Codex",
        )
        .unwrap();
        s.journal(
            "a",
            "task",
            Some("sqlite"),
            Some("done"),
            "Migration getestet",
            "cargo test, bestanden",
        )
        .unwrap();
        s.journal(
            "a",
            "task",
            Some("ui"),
            Some("open"),
            "Oberfläche planen",
            "Nutzer",
        )
        .unwrap();
        s.journal(
            "a",
            "decision",
            None,
            None,
            "SQLite bleibt Quelle",
            "Nutzerentscheidung",
        )
        .unwrap();
        s.journal("a", "next_step", None, None, "Fortsetzung prüfen", "Codex")
            .unwrap();
        s.append_message(&session, "user", "Was wurde gemacht?")
            .unwrap();
        s.append_message(&session, "assistant", "Die Migration wurde implementiert.")
            .unwrap();
    }
    let s = MemoryStore::open_existing(&path.0).unwrap();
    let resume = s.resume("a", None).unwrap();
    assert_eq!(s.default_conversation("a").unwrap(), session);
    assert_eq!(resume.goal.unwrap().body, "V-Mind bauen");
    assert_eq!(resume.tasks.len(), 2);
    assert_eq!(resume.task_count, 2);
    assert_eq!(resume.tasks[0].task_key.as_deref(), Some("ui"));
    assert_eq!(resume.tasks[1].task_status.as_deref(), Some("done"));
    assert_eq!(resume.decisions[0].body, "SQLite bleibt Quelle");
    assert_eq!(resume.next_step.unwrap().body, "Fortsetzung prüfen");
    assert_eq!(resume.total_events, 6);
    assert_eq!(
        resume.chat_tail.last().unwrap().content,
        "Die Migration wurde implementiert."
    );
    assert_eq!(resume.message_count, 2);
    assert_eq!(s.stats("a").unwrap().validated, 0);
}
#[test]
fn project_context_is_isolated_and_does_not_create_sessions_on_read() {
    let s = MemoryStore::in_memory().unwrap();
    s.journal("global", "goal", None, None, "Fremdes Ziel", "Test")
        .unwrap();
    let id = s.create_conversation("a", "Testgespräch").unwrap();
    s.append_message(&id, "assistant", "Privat in a").unwrap();
    let r = s.resume("b", None).unwrap();
    assert!(r.goal.is_none());
    assert!(r.chat_tail.is_empty());
    assert!(s.conversations("b").unwrap().is_empty());
    assert!(s.resume("b", Some(&id)).is_err());
    assert!(s.resume("a", Some("nicht-vorhanden")).is_err());
    assert!(s.append_message("nicht-vorhanden", "user", "Text").is_err());
}
#[test]
fn full_history_is_paginated_while_resume_remains_bounded() {
    let s = MemoryStore::in_memory().unwrap();
    let id = s.default_conversation("p").unwrap();
    for n in 0..35 {
        s.journal(
            "p",
            "task",
            Some(&format!("task-{n}")),
            Some("done"),
            &format!("Schritt {n}"),
            "Test",
        )
        .unwrap();
        s.append_message(&id, "assistant", &format!("Antwort {n}"))
            .unwrap();
    }
    let r = s.resume("p", None).unwrap();
    assert_eq!(r.tasks.len(), 20);
    assert_eq!(r.task_count, 35);
    assert_eq!(r.recent_events.len(), 10);
    assert_eq!(r.total_events, 35);
    assert_eq!(r.chat_tail.len(), 10);
    assert_eq!(r.message_count, 35);
    assert_eq!(r.chat_tail.last().unwrap().content, "Antwort 34");
    let first = s.journal_page("p", 0, 20).unwrap();
    let next = s.journal_page("p", first.last().unwrap().id, 20).unwrap();
    assert_eq!(first.len() + next.len(), 35);
    assert!(first.last().unwrap().id < next[0].id);
    let first = s.messages(&id, 0, 20).unwrap();
    let next = s.messages(&id, first.last().unwrap().id, 20).unwrap();
    assert_eq!(first.len() + next.len(), 35);
}
#[test]
fn invalid_project_events_and_messages_are_rejected() {
    let s = MemoryStore::in_memory().unwrap();
    let id = s.default_conversation("p").unwrap();
    assert!(s.journal("p", "task", None, None, "Text", "Test").is_err());
    assert!(
        s.journal("p", "task", Some("x"), Some("fantasy"), "Text", "Test")
            .is_err()
    );
    assert!(
        s.journal("p", "goal", Some("x"), Some("done"), "Text", "Test")
            .is_err()
    );
    assert!(s.journal("p", "goal", None, None, " ", "Test").is_err());
    assert!(s.append_message(&id, "system", "Anweisung").is_err());
    assert!(s.append_message(&id, "assistant", " ").is_err());
    assert!(s.messages(&id, -1, 10).is_err());
    assert!(s.journal_page("p", 0, 101).is_err());
    assert_eq!(s.resume("p", None).unwrap().total_events, 0);
}
#[test]
fn v2_upgrade_preserves_knowledge_and_starts_with_empty_project_history() {
    let path = Temp::new();
    {
        let c = rusqlite::Connection::open(&path.0).unwrap();
        c.execute_batch(include_str!("../../../migrations/0001_memory.sql"))
            .unwrap();
        c.execute_batch(include_str!("../../../migrations/0002_retrieval.sql"))
            .unwrap();
        c.execute_batch("PRAGMA user_version=2; INSERT INTO memories(kind,problem,solution,source) VALUES('long_term','Alt','Wissen','Test');").unwrap();
    }
    let s = MemoryStore::open_existing(&path.0).unwrap();
    assert_eq!(s.get(1).unwrap().unwrap().problem, "Alt");
    assert_eq!(s.resume("p", None).unwrap().total_events, 0);
    assert_eq!(s.stats("p").unwrap().schema_version, 4);
}
