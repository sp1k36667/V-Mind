use rusqlite::Connection;
use std::{
    fs,
    path::{Path, PathBuf},
};
use vmind_core::{MemoryStore, backup_database, inspect_database, set_journal_mode};

struct Temp(PathBuf);
impl Temp {
    fn new() -> Self {
        let p = std::env::temp_dir().join(format!(
            "vmind-journal-mode-{}-{}",
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
        self.0.join("wissen.db")
    }
}
impl Drop for Temp {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn sidecar(db: &Path, suffix: &str) -> PathBuf {
    let mut name = db.as_os_str().to_os_string();
    name.push(suffix);
    PathBuf::from(name)
}

fn with_entry(path: &Path) -> i64 {
    let s = MemoryStore::open(path).unwrap();
    let id = s
        .remember("long_term", "Journalmodus Prüfung", "WAL", "Test")
        .unwrap();
    s.validate(id, "Prüfer", "Test bestanden").unwrap();
    id
}

#[test]
fn new_databases_keep_the_default_journal_mode() {
    let t = Temp::new();
    with_entry(&t.db());
    assert_eq!(inspect_database(t.db()).unwrap().journal_mode, "delete");
}

#[test]
fn switching_to_wal_makes_a_verified_backup_first_and_reports_the_change() {
    let t = Temp::new();
    let id = with_entry(&t.db());
    let report = set_journal_mode(t.db(), "wal").unwrap();
    assert_eq!(
        (report.previous.as_str(), report.current.as_str()),
        ("delete", "wal")
    );
    assert!(report.changed);
    let backup = PathBuf::from(report.backup.expect("Sicherung angelegt"));
    assert!(inspect_database(&backup).unwrap().healthy);
    assert_eq!(
        MemoryStore::open_existing(&backup)
            .unwrap()
            .recall("Journalmodus", "global", 5)
            .unwrap()[0]
            .id,
        id
    );
    assert_eq!(inspect_database(t.db()).unwrap().journal_mode, "wal");
    let again = set_journal_mode(t.db(), "wal").unwrap();
    assert!(!again.changed);
    assert!(again.backup.is_none(), "keine Sicherung ohne Änderung");
}

#[test]
fn read_only_tools_work_on_wal_databases_after_all_connections_closed() {
    let t = Temp::new();
    let id = with_entry(&t.db());
    set_journal_mode(t.db(), "wal").unwrap();
    {
        let s = MemoryStore::open_existing(t.db()).unwrap();
        s.journal("p", "note", None, None, "nach dem Wechsel", "Test")
            .unwrap();
    }
    assert!(
        !sidecar(&t.db(), "-wal").exists()
            || fs::metadata(sidecar(&t.db(), "-wal")).unwrap().len() == 0
    );
    let report = inspect_database(t.db()).unwrap();
    assert!(report.healthy);
    assert_eq!(report.journal_mode, "wal");
    let copy = t.0.join("kopie.db");
    assert!(backup_database(t.db(), &copy).unwrap().verified);
    let lesend = MemoryStore::open_read_only(t.db()).unwrap();
    assert_eq!(
        lesend.recall("Journalmodus", "global", 5).unwrap()[0].id,
        id
    );
    assert_eq!(lesend.journal_page("p", 0, 10).unwrap().len(), 1);
}

#[test]
fn switching_back_to_delete_keeps_data_and_removes_sidecars_after_close() {
    let t = Temp::new();
    let id = with_entry(&t.db());
    set_journal_mode(t.db(), "wal").unwrap();
    let report = set_journal_mode(t.db(), "delete").unwrap();
    assert_eq!(
        (report.previous.as_str(), report.current.as_str()),
        ("wal", "delete")
    );
    assert!(!sidecar(&t.db(), "-wal").exists());
    assert!(!sidecar(&t.db(), "-shm").exists());
    let s = MemoryStore::open_existing(t.db()).unwrap();
    assert_eq!(s.recall("Journalmodus", "global", 5).unwrap()[0].id, id);
    assert_eq!(inspect_database(t.db()).unwrap().journal_mode, "delete");
}

#[test]
fn switching_while_another_connection_reads_fails_clearly_and_keeps_the_mode() {
    let t = Temp::new();
    with_entry(&t.db());
    let other = Connection::open(t.db()).unwrap();
    other.execute_batch("BEGIN").unwrap();
    let _: i64 = other
        .query_row("SELECT count(*) FROM memories", [], |r| r.get(0))
        .unwrap();
    let error = set_journal_mode(t.db(), "wal").unwrap_err().to_string();
    assert!(error.contains("anderen Prozess"), "{error}");
    other.execute_batch("COMMIT").unwrap();
    drop(other);
    assert_eq!(inspect_database(t.db()).unwrap().journal_mode, "delete");
}

#[test]
fn unknown_modes_are_rejected_without_touching_the_file() {
    let t = Temp::new();
    fs::write(t.db(), b"kein SQLite").unwrap();
    for mode in ["truncate", "WAL2", "", "memory"] {
        let error = set_journal_mode(t.db(), mode).unwrap_err().to_string();
        assert!(error.contains("wal oder delete"), "{mode}: {error}");
    }
    assert_eq!(fs::read(t.db()).unwrap(), b"kein SQLite");
}

#[cfg(unix)]
#[test]
fn wal_sidecars_are_private_like_the_database() {
    use std::os::unix::fs::PermissionsExt;
    let t = Temp::new();
    with_entry(&t.db());
    set_journal_mode(t.db(), "wal").unwrap();
    let s = MemoryStore::open_existing(t.db()).unwrap();
    s.journal("p", "note", None, None, "offen", "Test").unwrap();
    for suffix in ["-wal", "-shm"] {
        let mode = fs::metadata(sidecar(&t.db(), suffix))
            .unwrap()
            .permissions()
            .mode();
        assert_eq!(mode & 0o077, 0, "{suffix} für andere lesbar: {mode:o}");
    }
}
