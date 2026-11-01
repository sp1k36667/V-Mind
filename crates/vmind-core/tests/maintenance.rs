use rusqlite::Connection;
use std::{
    fs,
    path::{Path, PathBuf},
};
use vmind_core::{MemoryStore, backup_database, inspect_database};

struct Temp(PathBuf);
impl Temp {
    fn new() -> Self {
        let p = std::env::temp_dir().join(format!(
            "vmind-maintenance-{}-{}",
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
        self.0.join("source.db")
    }
}
impl Drop for Temp {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}
fn legacy(path: &Path) {
    let c = Connection::open(path).unwrap();
    for sql in [
        include_str!("../../../migrations/0001_memory.sql"),
        include_str!("../../../migrations/0002_retrieval.sql"),
        include_str!("../../../migrations/0003_project_context.sql"),
        include_str!("../../../migrations/0004_checks.sql"),
    ] {
        c.execute_batch(sql).unwrap();
    }
    c.pragma_update(None, "user_version", 4).unwrap();
    c.execute("INSERT INTO memories(kind,problem,solution,source) VALUES('long_term','alt','bewahren','Test')", []).unwrap();
}
#[test]
fn inspection_is_read_only_and_rejects_missing_foreign_and_future_databases() {
    let t = Temp::new();
    let p = t.db();
    assert!(inspect_database(&p).is_err());
    assert!(!p.exists());
    legacy(&p);
    let before = fs::read(&p).unwrap();
    let report = inspect_database(&p).unwrap();
    assert!(report.healthy);
    assert!(report.migration_required);
    assert_eq!(report.schema_version, 4);
    assert_eq!(fs::read(&p).unwrap(), before);
    let c = Connection::open(&p).unwrap();
    c.pragma_update(None, "user_version", 999).unwrap();
    drop(c);
    let before = fs::read(&p).unwrap();
    let report = inspect_database(&p).unwrap();
    assert!(!report.compatible);
    assert!(!report.healthy);
    assert_eq!(fs::read(&p).unwrap(), before);
    let p = t.0.join("foreign.db");
    Connection::open(&p).unwrap();
    assert!(!inspect_database(p).unwrap().healthy);
}
#[test]
fn backup_preserves_knowledge_history_project_and_wal_commits() {
    let t = Temp::new();
    let p = t.db();
    let s = MemoryStore::open(&p).unwrap();
    let c = Connection::open(&p).unwrap();
    c.pragma_update(None, "journal_mode", "WAL").unwrap();
    let id = s
        .remember("long_term", "Schemamigrationen", "SQLite", "Test")
        .unwrap();
    s.validate(id, "Prüfer", "Test bestanden").unwrap();
    s.journal("p", "decision", None, None, "SQLite bleibt", "Nutzer")
        .unwrap();
    let session = s.default_conversation("p").unwrap();
    s.append_message(&session, "assistant", "Letzter Stand")
        .unwrap();
    let out = t.0.join("copy.db");
    let report = backup_database(&p, &out).unwrap();
    assert!(report.verified);
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        assert_eq!(
            fs::metadata(&out).unwrap().permissions().mode() & 0o777,
            0o600
        );
    }
    assert_eq!(report.schema_version, 5);
    let restored = MemoryStore::open_existing(out).unwrap();
    assert_eq!(restored.recall("Migration", "global", 5).unwrap()[0].id, id);
    assert_eq!(
        restored.resume("p", Some(&session)).unwrap().chat_tail[0].content,
        "Letzter Stand"
    );
    assert_eq!(
        restored.resume("p", None).unwrap().decisions[0].body,
        "SQLite bleibt"
    );
    assert!(inspect_database(&p).unwrap().healthy);
}
#[test]
fn backup_never_overwrites_even_empty_files_or_source() {
    let t = Temp::new();
    let p = t.db();
    MemoryStore::open(&p).unwrap();
    let before = fs::read(&p).unwrap();
    assert!(backup_database(&p, &p).is_err());
    assert_eq!(fs::read(&p).unwrap(), before);
    let out = t.0.join("existing.db");
    fs::write(&out, []).unwrap();
    assert!(backup_database(&p, &out).is_err());
    assert!(fs::read(out).unwrap().is_empty());
}
#[test]
fn migration_creates_verified_old_schema_snapshot_before_any_changes() {
    let t = Temp::new();
    let p = t.db();
    legacy(&p);
    MemoryStore::open_existing(&p).unwrap();
    let files = fs::read_dir(&t.0)
        .unwrap()
        .map(|x| x.unwrap().path())
        .collect::<Vec<_>>();
    let snapshots = files
        .iter()
        .filter(|x| {
            x.file_name()
                .unwrap()
                .to_string_lossy()
                .contains("before-schema-5")
        })
        .collect::<Vec<_>>();
    assert_eq!(snapshots.len(), 1);
    let old = inspect_database(snapshots[0]).unwrap();
    assert!(old.healthy);
    assert_eq!(old.schema_version, 4);
    let c = Connection::open(snapshots[0]).unwrap();
    assert_eq!(
        c.query_row("SELECT problem FROM memories", [], |r| r
            .get::<_, String>(0))
            .unwrap(),
        "alt"
    );
    assert_eq!(inspect_database(p).unwrap().schema_version, 5);
}
#[test]
fn unhealthy_snapshot_fails_and_leaves_no_successful_backup() {
    let t = Temp::new();
    let p = t.db();
    MemoryStore::open(&p).unwrap();
    let c = Connection::open(&p).unwrap();
    c.execute_batch("DROP TRIGGER memories_trigram_insert")
        .unwrap();
    drop(c);
    let report = inspect_database(&p).unwrap();
    assert!(!report.healthy);
    assert!(
        report
            .missing_objects
            .contains(&"memories_trigram_insert".into())
    );
    let out = t.0.join("bad.db");
    assert!(backup_database(&p, &out).is_err());
    assert!(!out.exists());
}

#[test]
fn failed_safety_backup_aborts_migration_without_changing_source() {
    let t = Temp::new();
    let p = t.db();
    legacy(&p);
    let c = Connection::open(&p).unwrap();
    c.execute_batch("DROP TRIGGER memories_fts_insert").unwrap();
    drop(c);
    let before = fs::read(&p).unwrap();
    assert!(MemoryStore::open_existing(&p).is_err());
    assert_eq!(fs::read(&p).unwrap(), before);
    assert_eq!(
        Connection::open(p)
            .unwrap()
            .query_row("PRAGMA user_version", [], |r| r.get::<_, i64>(0))
            .unwrap(),
        4
    );
}

#[test]
fn read_only_store_cannot_write_or_upgrade_legacy_files() {
    let t = Temp::new();
    let path = t.db();
    legacy(&path);
    let before = fs::read(&path).unwrap();
    assert!(MemoryStore::open_read_only(&path).is_err());
    assert_eq!(fs::read(&path).unwrap(), before);
    assert_eq!(fs::read_dir(&t.0).unwrap().count(), 1);
    let missing = t.0.join("missing.db");
    assert!(MemoryStore::open_read_only(&missing).is_err());
    assert!(!missing.exists());
    let current = t.0.join("current.db");
    MemoryStore::open(&current).unwrap();
    let reader = MemoryStore::open_read_only(&current).unwrap();
    assert!(
        reader
            .remember("long_term", "nicht", "schreiben", "Test")
            .is_err()
    );
    assert_eq!(reader.stats("global").unwrap().pending, 0);
}

#[test]
fn snapshot_keeps_counts_and_resume_consistent_while_another_connection_commits() {
    let t = Temp::new();
    let path = t.db();
    let writer = MemoryStore::open(&path).unwrap();
    let c = Connection::open(&path).unwrap();
    c.pragma_update(None, "journal_mode", "WAL").unwrap();
    let reader = MemoryStore::open_read_only(&path).unwrap();
    reader
        .read_snapshot(|s| {
            assert_eq!(s.stats("p")?.pending, 0);
            writer.remember_scoped("p", "long_term", "später", "sichtbar", "Test")?;
            writer.journal("p", "goal", None, None, "Späterer Stand", "Test")?;
            assert_eq!(s.stats("p")?.pending, 0);
            assert!(s.resume("p", None)?.goal.is_none());
            Ok(())
        })
        .unwrap();
    assert_eq!(reader.stats("p").unwrap().pending, 1);
    assert_eq!(
        reader.resume("p", None).unwrap().goal.unwrap().body,
        "Späterer Stand"
    );
}
