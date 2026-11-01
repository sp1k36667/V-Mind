use vmind_core::{MemoryStore, Observation};

fn obs(session: &str, id: &str, tool: &str, result: &str, paths: &[&str]) -> Observation {
    Observation {
        session_id: session.into(),
        tool_use_id: id.into(),
        tool: tool.into(),
        result: result.into(),
        paths: paths.iter().map(|p| p.to_string()).collect(),
    }
}

#[test]
fn same_report_is_stored_once_and_conflicting_reuse_is_rejected() {
    let s = MemoryStore::in_memory().unwrap();
    let first = obs(
        "s1",
        "t1",
        "Edit",
        "completed",
        &["src/b.rs", "src/a.rs", "src/a.rs"],
    );
    assert!(s.observe("p", &first).unwrap());
    // Hooks can fire twice; the identical report is not a second observation.
    let reordered = obs("s1", "t1", "Edit", "completed", &["src/a.rs", "src/b.rs"]);
    assert!(!s.observe("p", &reordered).unwrap());
    assert!(
        s.observe(
            "p",
            &obs("s1", "t1", "Edit", "failed", &["src/a.rs", "src/b.rs"])
        )
        .is_err()
    );
    assert!(s.observe("q", &reordered).is_err());
    assert_eq!(s.resume("p", None).unwrap().observation_count, 1);
}

#[test]
fn invalid_reports_are_rejected_without_storing_anything() {
    let s = MemoryStore::in_memory().unwrap();
    for bad in [
        obs(" ", "t", "Edit", "completed", &[]),
        obs("s", "", "Edit", "completed", &[]),
        obs("s", "t", "Read", "completed", &[]),
        obs("s", "t", "Edit", "passed", &[]),
        obs("s", "t", "Edit", "completed", &["a\nb"]),
        obs("s", &"x".repeat(201), "Edit", "completed", &[]),
    ] {
        assert!(s.observe("p", &bad).is_err());
    }
    assert!(
        s.observe(" ", &obs("s", "t", "Edit", "completed", &[]))
            .is_err()
    );
    assert_eq!(s.resume("p", None).unwrap().observation_count, 0);
}

#[test]
fn resume_summarizes_the_latest_sessions_without_flooding_the_journal() {
    let s = MemoryStore::in_memory().unwrap();
    s.journal(
        "p",
        "decision",
        None,
        None,
        "Entscheidung bleibt sichtbar",
        "Test",
    )
    .unwrap();
    for session in ["alt", "s2", "s3", "neu"] {
        for i in 0..4 {
            let path = format!("src/{session}-{}.rs", i % 2);
            let result = if i == 3 { "failed" } else { "completed" };
            let id = format!("{session}-{i}");
            s.observe("p", &obs(session, &id, "Write", result, &[path.as_str()]))
                .unwrap();
        }
    }
    s.observe("anderes", &obs("fremd", "f", "Bash", "completed", &[]))
        .unwrap();
    let r = s.resume("p", None).unwrap();
    assert_eq!(r.observation_count, 16);
    let ids: Vec<_> = r
        .observed_sessions
        .iter()
        .map(|x| x.session_id.as_str())
        .collect();
    assert_eq!(ids, ["neu", "s3", "s2"]);
    let latest = &r.observed_sessions[0];
    assert_eq!((latest.calls, latest.failed, latest.files), (4, 1, 2));
    assert_eq!(latest.paths, ["src/neu-1.rs", "src/neu-0.rs"]);
    // Observations stay out of the journal and do not push decisions aside.
    assert_eq!(r.total_events, 1);
    assert_eq!(r.decisions[0].body, "Entscheidung bleibt sichtbar");
    assert!(s.observed_sessions("p", 0).is_err());
    assert_eq!(s.observed_sessions("anderes", 5).unwrap().len(), 1);
}

#[test]
fn schema_5_upgrade_keeps_all_data_and_makes_a_verified_backup_first() {
    let dir = std::env::temp_dir().join(format!(
        "vmind-obs-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir(&dir).unwrap();
    let path = dir.join("v5.db");
    {
        let c = rusqlite::Connection::open(&path).unwrap();
        for sql in [
            include_str!("../../../migrations/0001_memory.sql"),
            include_str!("../../../migrations/0002_retrieval.sql"),
            include_str!("../../../migrations/0003_project_context.sql"),
            include_str!("../../../migrations/0004_checks.sql"),
            include_str!("../../../migrations/0005_partial_search.sql"),
        ] {
            c.execute_batch(sql).unwrap();
        }
        c.pragma_update(None, "user_version", 5).unwrap();
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
    // A hook must never trigger the upgrade.
    assert!(MemoryStore::open_current(&path).is_err());
    let s = MemoryStore::open_existing(&path).unwrap();
    assert_eq!(s.stats("global").unwrap().schema_version, 6);
    assert_eq!(s.get(1).unwrap().unwrap().problem, "alt");
    assert_eq!(s.resume("p", None).unwrap().decisions[0].body, "bleibt");
    assert!(
        s.observe("p", &obs("s", "t", "Bash", "completed", &[]))
            .unwrap()
    );
    let snapshots: Vec<_> = std::fs::read_dir(&dir)
        .unwrap()
        .map(|e| e.unwrap().path())
        .filter(|p| p.to_string_lossy().contains("before-schema-6"))
        .collect();
    assert_eq!(snapshots.len(), 1);
    let old = vmind_core::inspect_database(&snapshots[0]).unwrap();
    assert!(old.healthy);
    assert_eq!(old.schema_version, 5);
    assert!(MemoryStore::open_current(&path).is_ok());
    std::fs::remove_dir_all(dir).unwrap();
}
