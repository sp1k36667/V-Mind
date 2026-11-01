mod checks;
mod maintenance;
pub use maintenance::{BackupReport, DoctorReport, backup_database, inspect_database};
mod project;
pub use checks::{Applied, Check, CheckResult, CheckRun, Outcome};
pub use project::{ChatMessage, Conversation, JournalEntry, Resume};

const SCHEMA_VERSION: i64 = 5;

// Persistentes, modellunabhängiges Gedächtnis mit nachvollziehbarer Validierung.
use rusqlite::{Connection, OpenFlags, OptionalExtension, Result, params};
use serde::Serialize;
use std::path::Path;

pub struct MemoryStore {
    conn: Connection,
}

#[derive(Debug, PartialEq, Eq, Serialize)]
pub struct Memory {
    pub id: i64,
    pub kind: String,
    pub problem: String,
    pub solution: String,
}

#[derive(Debug, Serialize)]
pub struct Record {
    pub id: i64,
    pub scope: String,
    pub kind: String,
    pub problem: String,
    pub solution: String,
    pub source: String,
    pub status: String,
    pub validated_by: Option<String>,
    pub evidence: Option<String>,
    pub created_at: String,
    pub invalidated_by: Option<String>,
    pub invalidation_reason: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct Event {
    pub action: String,
    pub actor: String,
    pub reason: String,
    pub created_at: String,
}

#[derive(Debug, Serialize)]
pub struct Stats {
    pub schema_version: i64,
    pub pending: i64,
    pub validated: i64,
    pub invalidated: i64,
}

const FIELDS: &str = "m.id, m.scope, m.kind, m.problem, m.solution, m.source,
 CASE WHEN i.memory_id IS NOT NULL THEN 'invalidated' ELSE m.status END,
 m.validated_by, m.evidence, m.created_at, i.actor, i.reason";

fn record(row: &rusqlite::Row<'_>) -> Result<Record> {
    Ok(Record {
        id: row.get(0)?,
        scope: row.get(1)?,
        kind: row.get(2)?,
        problem: row.get(3)?,
        solution: row.get(4)?,
        source: row.get(5)?,
        status: row.get(6)?,
        validated_by: row.get(7)?,
        evidence: row.get(8)?,
        created_at: row.get(9)?,
        invalidated_by: row.get(10)?,
        invalidation_reason: row.get(11)?,
    })
}

/// Eigene Prüffehler. Diese rusqlite-Variante zeigt nur unsere Meldung an, ohne das
/// irreführende „Invalid parameter name:“ davor.
fn invalid(message: &str) -> rusqlite::Error {
    rusqlite::Error::ToSqlConversionFailure(message.into())
}

fn nonblank(value: &str) -> Result<()> {
    if value.trim().is_empty() {
        Err(invalid("Leere Pflichtangabe"))
    } else {
        Ok(())
    }
}

/// Suchbegriffe ohne Stoppwörter, klein geschrieben, ohne Dubletten, höchstens 24.
fn search_terms(query: &str) -> Vec<String> {
    let stop = [
        "der", "die", "das", "ein", "eine", "einer", "einem", "einen", "und", "oder", "ist",
        "sind", "mit", "für", "von", "zu", "im", "in", "am", "an", "wie", "was", "ich", "wir",
        "beim", "den", "dem", "des", "es", "the", "a", "an", "and", "or", "is", "to", "of", "how",
    ];
    let mut terms = Vec::new();
    for term in query
        .split(|c: char| !c.is_alphanumeric())
        .filter(|s| !s.is_empty())
    {
        let term = term.to_lowercase();
        if !stop.contains(&term.as_str()) && !terms.contains(&term) {
            terms.push(term);
        }
        if terms.len() == 24 {
            break;
        }
    }
    terms
}

// Nur gequotete Begriffe gelangen in MATCH, keine vom Aufrufer gelieferte FTS-Syntax.
fn match_expression<'a>(terms: impl Iterator<Item = &'a String>) -> String {
    terms
        .map(|t| format!("\"{t}\""))
        .collect::<Vec<_>>()
        .join(" OR ")
}

/// Der Trigramm-Index braucht mindestens drei Zeichen je Begriff.
const MIN_PARTIAL_TERM_CHARS: usize = 3;

/// Legt eine noch nicht vorhandene Datenbankdatei unter Unix nur für den Besitzer
/// lesbar an (0600). Vorhandene Dateien, `:memory:` und SQLite-URIs bleiben unberührt.
fn create_private(path: &Path) -> Result<()> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        let name = path.to_string_lossy();
        if name.is_empty() || name == ":memory:" || name.starts_with("file:") {
            return Ok(());
        }
        let created = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(0o600)
            .open(path);
        match created {
            Ok(_) => {}
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {}
            Err(e) => return Err(invalid(&format!("Datenbankdatei nicht anlegbar: {e}"))),
        }
    }
    #[cfg(not(unix))]
    let _ = path;
    Ok(())
}

impl MemoryStore {
    pub fn open(path: impl AsRef<Path>) -> Result<Self> {
        create_private(path.as_ref())?;
        Self::from_connection(Connection::open(path)?)
    }
    /// Öffnet nur eine vorhandene Datei, verhindert versehentliche neue Datenbanken bei Tippfehlern.
    pub fn open_existing(path: impl AsRef<Path>) -> Result<Self> {
        Self::from_connection(Connection::open_with_flags(
            path,
            OpenFlags::SQLITE_OPEN_READ_WRITE,
        )?)
    }
    /// Reads only an existing current-schema database; never creates or upgrades.
    pub fn open_read_only(path: impl AsRef<Path>) -> Result<Self> {
        let conn = Connection::open_with_flags(path, OpenFlags::SQLITE_OPEN_READ_ONLY)?;
        conn.busy_timeout(std::time::Duration::from_secs(5))?;
        let version: i64 = conn.query_row("PRAGMA user_version", [], |r| r.get(0))?;
        if version != SCHEMA_VERSION {
            return Err(invalid(
                "Lesender Zugriff benötigt das aktuelle Schema; zuerst doctor, backup und ein bewusstes Upgrade ausführen",
            ));
        }
        conn.pragma_update(None, "foreign_keys", true)?;
        Ok(Self { conn })
    }
    /// Keeps several reads in one consistent SQLite snapshot. The callback must
    /// only read; use open_read_only when this must also be enforced by SQLite.
    pub fn read_snapshot<T>(&self, read: impl FnOnce(&Self) -> Result<T>) -> Result<T> {
        let tx = self.conn.unchecked_transaction()?;
        let result = read(self)?;
        tx.commit()?;
        Ok(result)
    }
    pub fn in_memory() -> Result<Self> {
        Self::from_connection(Connection::open_in_memory()?)
    }
    fn from_connection(mut conn: Connection) -> Result<Self> {
        conn.busy_timeout(std::time::Duration::from_secs(5))?;
        conn.pragma_update(None, "foreign_keys", true)?;
        let version: i64 = conn.query_row("PRAGMA user_version", [], |r| r.get(0))?;
        if version == SCHEMA_VERSION {
            return Ok(Self { conn });
        }
        if !(0..=SCHEMA_VERSION).contains(&version) {
            return Err(invalid("Unbekannte Datenbankversion"));
        }
        let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
        let mut version: i64 = tx.query_row("PRAGMA user_version", [], |r| r.get(0))?;
        if !(0..=SCHEMA_VERSION).contains(&version) {
            return Err(invalid("Unbekannte Datenbankversion"));
        }
        // The IMMEDIATE transaction serializes migrations and freezes the committed
        // source while a separate read-only connection makes the safety snapshot.
        if (1..SCHEMA_VERSION).contains(&version)
            && let Some(path) = tx.path().filter(|p| !p.is_empty())
        {
            maintenance::backup_before_migration(Path::new(path))?;
        }
        if version == 0 {
            tx.execute_batch(include_str!("../../../migrations/0001_memory.sql"))?;
            version = 1;
        }
        if version == 1 {
            tx.execute_batch(include_str!("../../../migrations/0002_retrieval.sql"))?;
            version = 2;
        }
        if version == 2 {
            tx.execute_batch(include_str!("../../../migrations/0003_project_context.sql"))?;
            version = 3;
        }
        if version == 3 {
            tx.execute_batch(include_str!("../../../migrations/0004_checks.sql"))?;
            version = 4;
        }
        if version == 4 {
            tx.execute_batch(include_str!("../../../migrations/0005_partial_search.sql"))?;
        }
        tx.pragma_update(None, "user_version", SCHEMA_VERSION)?;
        tx.commit()?;
        Ok(Self { conn })
    }
    pub fn remember(&self, kind: &str, problem: &str, solution: &str, source: &str) -> Result<i64> {
        self.remember_scoped("global", kind, problem, solution, source)
    }
    pub fn remember_scoped(
        &self,
        scope: &str,
        kind: &str,
        problem: &str,
        solution: &str,
        source: &str,
    ) -> Result<i64> {
        for value in [scope, kind, problem, solution, source] {
            nonblank(value)?;
        }
        if scope.chars().count() > 128
            || source.chars().count() > 4000
            || problem.chars().count() > 16000
            || solution.chars().count() > 16000
        {
            return Err(invalid("Eintrag überschreitet die Größenlimits"));
        }
        self.conn.execute(
            "INSERT INTO memories(scope, kind, problem, solution, source) VALUES (?1, ?2, ?3, ?4, ?5)",
            params![scope, kind, problem, solution, source])?;
        Ok(self.conn.last_insert_rowid())
    }
    /// Dokumentiert eine externe Prüfung, keine automatische Wahrheitsprüfung.
    pub fn validate(&self, id: i64, reviewer: &str, evidence: &str) -> Result<bool> {
        nonblank(reviewer)?;
        nonblank(evidence)?;
        Ok(self.conn.execute(
            "UPDATE memories SET status='validated', validated_by=?2, evidence=?3
             WHERE id=?1 AND status='pending'
             AND NOT EXISTS(SELECT 1 FROM invalidations WHERE memory_id=?1)",
            params![id, reviewer, evidence],
        )? == 1)
    }
    /// Zurückgezogene Einträge bleiben einsehbar, werden aber nicht mehr abgerufen.
    pub fn invalidate(&self, id: i64, actor: &str, reason: &str) -> Result<bool> {
        nonblank(actor)?;
        nonblank(reason)?;
        Ok(self.conn.execute(
            "INSERT INTO invalidations(memory_id, actor, reason)
             SELECT id, ?2, ?3 FROM memories WHERE id=?1
             AND NOT EXISTS(SELECT 1 FROM invalidations WHERE memory_id=?1)",
            params![id, actor, reason],
        )? == 1)
    }
    pub fn get(&self, id: i64) -> Result<Option<Record>> {
        self.conn
            .query_row(
                &format!(
                    "SELECT {FIELDS} FROM memories m
            LEFT JOIN invalidations i ON i.memory_id=m.id WHERE m.id=?1"
                ),
                [id],
                record,
            )
            .optional()
    }
    pub fn history(&self, id: i64) -> Result<Vec<Event>> {
        let mut stmt = self.conn.prepare(
            "SELECT action, actor, reason, created_at
            FROM memory_events WHERE memory_id=?1 ORDER BY id",
        )?;
        stmt.query_map([id], |row| {
            Ok(Event {
                action: row.get(0)?,
                actor: row.get(1)?,
                reason: row.get(2)?,
                created_at: row.get(3)?,
            })
        })?
        .collect()
    }
    /// Alte wörtliche Suche, auf globale validierte aktive Einträge begrenzt.
    pub fn search(&self, query: &str) -> Result<Vec<Memory>> {
        if query.trim().is_empty() {
            return Ok(Vec::new());
        }
        let mut stmt = self.conn.prepare(
            "SELECT m.id, m.kind, m.problem, m.solution FROM memories m
            WHERE m.scope='global' AND m.status='validated'
            AND NOT EXISTS(SELECT 1 FROM invalidations i WHERE i.memory_id=m.id)
            AND (instr(m.problem, ?1)>0 OR instr(m.solution, ?1)>0) ORDER BY m.id LIMIT 100",
        )?;
        stmt.query_map([query], |r| {
            Ok(Memory {
                id: r.get(0)?,
                kind: r.get(1)?,
                problem: r.get(2)?,
                solution: r.get(3)?,
            })
        })?
        .collect()
    }
    /// BM25-Volltextsuche, nur validierte aktive Einträge; Projekt plus global.
    /// Zuerst ganze Wörter, danach füllen Teilworttreffer auf (Beugungen, Komposita).
    pub fn recall(&self, query: &str, scope: &str, limit: usize) -> Result<Vec<Record>> {
        nonblank(scope)?;
        if query.chars().count() > 2000 {
            return Err(invalid("Suchtext zu lang"));
        }
        if !(1..=20).contains(&limit) {
            return Err(invalid("Limit muss 1 bis 20 sein"));
        }
        let terms = search_terms(query);
        let mut found = self.ranked(
            "memories_fts",
            &match_expression(terms.iter()),
            scope,
            limit,
        )?;
        if found.len() < limit {
            let partial = match_expression(
                terms
                    .iter()
                    .filter(|t| t.chars().count() >= MIN_PARTIAL_TERM_CHARS),
            );
            for extra in self.ranked("memories_trigram", &partial, scope, limit)? {
                if found.len() == limit {
                    break;
                }
                if !found.iter().any(|r| r.id == extra.id) {
                    found.push(extra);
                }
            }
        }
        Ok(found)
    }
    /// Validierte aktive Treffer eines FTS-Index im Bereich plus global, nach BM25.
    fn ranked(
        &self,
        index: &str,
        expression: &str,
        scope: &str,
        limit: usize,
    ) -> Result<Vec<Record>> {
        if expression.is_empty() {
            return Ok(Vec::new());
        }
        let mut stmt = self.conn.prepare(&format!(
            "SELECT {FIELDS}
            FROM {index} JOIN memories m ON m.id={index}.rowid
            LEFT JOIN invalidations i ON i.memory_id=m.id
            WHERE {index} MATCH ?1 AND m.status='validated' AND i.memory_id IS NULL
            AND m.scope IN ('global', ?2)
            ORDER BY bm25({index}, 2.0, 1.0), m.id LIMIT ?3"
        ))?;
        stmt.query_map(params![expression, scope, limit as i64], record)?
            .collect()
    }
    pub fn pending(&self, scope: &str) -> Result<Vec<Record>> {
        nonblank(scope)?;
        let mut stmt = self.conn.prepare(&format!(
            "SELECT {FIELDS} FROM memories m
            LEFT JOIN invalidations i ON i.memory_id=m.id
            WHERE m.status='pending' AND i.memory_id IS NULL AND m.scope IN ('global', ?1)
            ORDER BY m.id LIMIT 100"
        ))?;
        stmt.query_map([scope], record)?.collect()
    }
    /// Validierte aktive Einträge im Bereich plus global, neueste zuerst.
    pub fn validated(&self, scope: &str, limit: usize) -> Result<Vec<Record>> {
        nonblank(scope)?;
        if !(1..=100).contains(&limit) {
            return Err(invalid("Limit muss 1 bis 100 sein"));
        }
        let mut stmt = self.conn.prepare(&format!(
            "SELECT {FIELDS} FROM memories m
            LEFT JOIN invalidations i ON i.memory_id=m.id
            WHERE m.status='validated' AND i.memory_id IS NULL AND m.scope IN ('global', ?1)
            ORDER BY m.id DESC LIMIT ?2"
        ))?;
        stmt.query_map(params![scope, limit as i64], record)?
            .collect()
    }
    pub fn stats(&self, scope: &str) -> Result<Stats> {
        nonblank(scope)?;
        self.conn.query_row(
            "SELECT
            (SELECT user_version FROM pragma_user_version),
            count(CASE WHEN m.status='pending' AND i.memory_id IS NULL THEN 1 END),
            count(CASE WHEN m.status='validated' AND i.memory_id IS NULL THEN 1 END),
            count(i.memory_id)
            FROM memories m LEFT JOIN invalidations i ON i.memory_id=m.id
            WHERE m.scope IN ('global', ?1)",
            [scope],
            |row| {
                Ok(Stats {
                    schema_version: row.get(0)?,
                    pending: row.get(1)?,
                    validated: row.get(2)?,
                    invalidated: row.get(3)?,
                })
            },
        )
    }
}
