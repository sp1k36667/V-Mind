//! Maintenance never opens a source through MemoryStore: inspection and snapshots
//! must preserve old schemas so that they are useful before an upgrade.
use crate::{SCHEMA_VERSION, invalid};
use rusqlite::{
    Connection, OpenFlags, Result,
    backup::{Backup, StepResult},
};
use serde::Serialize;
use std::{
    fs,
    path::Path,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

#[derive(Debug, Serialize)]
pub struct DoctorReport {
    pub schema_version: i64,
    pub supported_schema_version: i64,
    pub compatible: bool,
    pub migration_required: bool,
    pub healthy: bool,
    pub integrity_errors: Vec<String>,
    pub foreign_key_violations: usize,
    pub missing_objects: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct BackupReport {
    pub destination: String,
    pub schema_version: i64,
    pub verified: bool,
    pub bytes: u64,
}

fn read_only(path: &Path) -> Result<Connection> {
    let conn = Connection::open_with_flags(path, OpenFlags::SQLITE_OPEN_READ_ONLY)?;
    conn.busy_timeout(Duration::from_secs(5))?;
    Ok(conn)
}

fn inspect(conn: &Connection) -> Result<DoctorReport> {
    // One snapshot for every diagnostic, including when another client writes.
    let tx = conn.unchecked_transaction()?;
    let version = tx.query_row("PRAGMA user_version", [], |r| r.get::<_, i64>(0))?;
    let integrity = tx
        .prepare("PRAGMA integrity_check")?
        .query_map([], |r| r.get::<_, String>(0))?
        .collect::<Result<Vec<_>>>()?;
    let integrity_errors = integrity
        .into_iter()
        .filter(|v| v != "ok")
        .collect::<Vec<_>>();
    let foreign_key_violations = tx
        .prepare("PRAGMA foreign_key_check")?
        .query_map([], |_| Ok(()))?
        .collect::<Result<Vec<_>>>()?
        .len();
    let mut required = vec!["memories"];
    if version >= 2 {
        required.extend([
            "invalidations",
            "memory_events",
            "memories_fts",
            "memory_created",
            "memory_validated",
            "memory_invalidated",
            "memories_fts_insert",
            "memories_fts_delete",
            "memories_fts_update",
        ]);
    }
    if version >= 3 {
        required.extend(["project_journal", "conversations", "chat_messages"]);
    }
    if version >= 4 {
        required.extend(["memory_checks", "check_runs"]);
    }
    if version >= 5 {
        required.extend([
            "memories_trigram",
            "memories_trigram_insert",
            "memories_trigram_delete",
            "memories_trigram_update",
        ]);
    }
    if version >= 6 {
        required.extend(["observations", "observations_scope_session"]);
    }
    let mut missing_objects = Vec::new();
    for name in required {
        let exists: bool = tx.query_row(
            "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE name=?1)",
            [name],
            |r| r.get(0),
        )?;
        if !exists {
            missing_objects.push(name.into());
        }
    }
    let compatible = (1..=SCHEMA_VERSION).contains(&version);
    let healthy = compatible
        && integrity_errors.is_empty()
        && foreign_key_violations == 0
        && missing_objects.is_empty();
    tx.commit()?;
    Ok(DoctorReport {
        schema_version: version,
        supported_schema_version: SCHEMA_VERSION,
        compatible,
        migration_required: compatible && version < SCHEMA_VERSION,
        healthy,
        integrity_errors,
        foreign_key_violations,
        missing_objects,
    })
}

/// Read-only, including for old and future databases. Never creates or migrates.
pub fn inspect_database(path: impl AsRef<Path>) -> Result<DoctorReport> {
    inspect(&read_only(path.as_ref())?)
}

/// Consistent SQLite snapshot, preserving the original schema. Never overwrites
/// an existing destination, even if it is empty. Success includes integrity checks.
/// An interrupted process may leave an incomplete destination; inspect it before use.
pub fn backup_database(
    source: impl AsRef<Path>,
    destination: impl AsRef<Path>,
) -> Result<BackupReport> {
    let source = read_only(source.as_ref())?;
    let destination = destination.as_ref();
    // Exclusive creation also protects the source, aliases, symlinks and empty files.
    let mut options = fs::OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    options.open(destination).map_err(|e| {
        invalid(&format!(
            "Sicherungsziel kann nicht neu angelegt werden: {e}"
        ))
    })?;
    let result = (|| {
        // SQLite interprets relative names beginning with file: as URIs even when
        // the filesystem reserved a literal name. Bind it to the actual new file
        // before SQLite sees it, so URI options can never redirect a backup.
        let physical_destination = fs::canonicalize(destination)
            .map_err(|e| invalid(&format!("Sicherungsziel nicht auflösbar: {e}")))?;
        let mut target =
            Connection::open_with_flags(&physical_destination, OpenFlags::SQLITE_OPEN_READ_WRITE)?;
        {
            let backup = Backup::new(&source, &mut target)?;
            let started = Instant::now();
            loop {
                match backup.step(128)? {
                    StepResult::Done => break,
                    StepResult::More | StepResult::Busy | StepResult::Locked => {
                        if started.elapsed() >= Duration::from_secs(30) {
                            return Err(invalid("Zeitlimit beim Sichern überschritten"));
                        }
                        std::thread::sleep(Duration::from_millis(5));
                    }
                    _ => return Err(invalid("Unbekannter Sicherungsstatus")),
                }
            }
        }
        let report = inspect(&target)?;
        if !report.healthy {
            return Err(invalid(
                "Sicherung hat die Integritäts- und Schemaprüfung nicht bestanden",
            ));
        }
        drop(target);
        let file = fs::OpenOptions::new()
            .read(true)
            .write(true)
            .open(&physical_destination)
            .map_err(|e| invalid(&format!("Sicherungsdatei nicht lesbar: {e}")))?;
        file.sync_all()
            .map_err(|e| invalid(&format!("Sicherung nicht auf Datenträger bestätigt: {e}")))?;
        Ok(BackupReport {
            destination: destination.display().to_string(),
            schema_version: report.schema_version,
            verified: true,
            bytes: file.metadata().map_err(|e| invalid(&e.to_string()))?.len(),
        })
    })();
    if result.is_err() {
        // Only the file exclusively created above belongs to this attempt.
        let _ = fs::remove_file(destination);
    }
    result
}

pub(crate) fn backup_before_migration(source: &Path) -> Result<()> {
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|e| invalid(&e.to_string()))?
        .as_nanos();
    let directory = std::env::var_os("VMIND_BACKUP_DIR");
    let destination = if let Some(directory) = directory {
        if directory.is_empty() {
            return Err(invalid(
                "VMIND_BACKUP_DIR darf nicht leer sein; Sicherung wird nicht übersprungen",
            ));
        }
        let name = source
            .file_name()
            .ok_or_else(|| invalid("Datenbank-Dateiname fehlt"))?;
        Path::new(&directory).join(name)
    } else {
        source.to_path_buf()
    };
    let mut name = destination.as_os_str().to_os_string();
    name.push(format!(
        ".before-schema-{SCHEMA_VERSION}-{stamp}-{}.db",
        std::process::id()
    ));
    let report = backup_database(source, Path::new(&name)).map_err(|error| {
        invalid(&format!(
            "Migration abgebrochen, Sicherung fehlgeschlagen: {error}. \
            Speicherplatz und Schreibrechte prüfen; VMIND_BACKUP_DIR auf einen vorhandenen \
            beschreibbaren Sicherungsordner setzen. Keine Sicherung wird übersprungen."
        ))
    })?;
    eprintln!(
        "V-Mind: geprüfte Sicherung vor Migration: {}",
        report.destination
    );
    Ok(())
}
