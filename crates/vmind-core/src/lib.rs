mod audit;
pub use audit::{AuditFinding, AuditReport, ScannedTable, audit_secrets};
mod check_evidence;
mod checks;
pub use check_evidence::{CheckEvidence, CheckState, CheckVerdict};
mod maintenance;
pub use maintenance::{
    BackupReport, DoctorReport, JournalModeReport, backup_database, inspect_database,
    set_journal_mode,
};
mod observations;
mod paths;
mod project;
mod repairs;
mod secrets;
pub use checks::{Applied, Check, CheckResult, CheckRun, Outcome};
pub use observations::{Observation, SessionSummary};
pub use paths::literal_file_path;
pub use project::{ChatMessage, Conversation, JournalEntry, Resume};
pub use repairs::{OpenRepairs, Repair};
pub use secrets::SecretKind;

const SCHEMA_VERSION: i64 = 6;

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
    pub check: CheckEvidence,
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
        check: CheckEvidence::default(),
    })
}

/// Eigene Prüffehler. Diese rusqlite-Variante zeigt nur unsere Meldung an, ohne das
/// irreführende „Invalid parameter name:“ davor.
fn invalid(message: &str) -> rusqlite::Error {
    rusqlite::Error::ToSqlConversionFailure(message.into())
}

/// Zusätzliche Versuche nach SQLITE_BUSY. busy_timeout wartet je Versuch bis zu 5 s; schreibt
/// ein anderer Prozess dauerhaft, kann ein Schreiber trotzdem leer ausgehen.
const BUSY_RETRIES: u32 = 4;

fn is_busy(error: &rusqlite::Error) -> bool {
    matches!(error, rusqlite::Error::SqliteFailure(e, _) if e.code == rusqlite::ErrorCode::DatabaseBusy)
}

/// Kurze, leicht gestreute Pause, damit sich zwei wartende Schreiber nicht im Gleichtakt treffen.
fn busy_backoff(attempt: u32) -> std::time::Duration {
    let streuung = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |d| d.subsec_nanos() % 50);
    std::time::Duration::from_millis(u64::from(25 * attempt + streuung))
}

/// Wiederholt einen einzelnen Schreibbefehl begrenzt, wenn SQLite SQLITE_BUSY meldet. Nur
/// außerhalb einer ausdrücklichen Transaktion: Dort hat ein mit SQLITE_BUSY gescheiterter Befehl
/// laut SQLite-Dokumentation nichts geschrieben und darf wiederholt werden, es entstehen keine
/// Duplikate. Innerhalb einer Transaktion wird der Fehler unverändert weitergegeben.
fn retry_busy<T>(conn: &Connection, mut write: impl FnMut() -> Result<T>) -> Result<T> {
    let mut attempt = 0;
    loop {
        match write() {
            Err(error) if is_busy(&error) && attempt < BUSY_RETRIES && conn.is_autocommit() => {
                attempt += 1;
                std::thread::sleep(busy_backoff(attempt));
            }
            other => return other,
        }
    }
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

/// Höchstens eine dieser Endungen wird für die Wortformsuche abgetrennt, die längste zuerst.
const WORD_FORM_SUFFIXES: &[&str] = &["ern", "en", "er", "es", "e", "n", "s"];
const MIN_WORD_FORM_INPUT_CHARS: usize = 5;
const MIN_WORD_FORM_STEM_CHARS: usize = 4;
/// Funktionswörter, die in der Wortformsuche nur Beifang brächten. Die ersten Stufen der
/// Suche bleiben davon unberührt.
const WORD_FORM_STOP_WORDS: &[&str] = &[
    "nicht", "kein", "keine", "keinen", "nach", "ohne", "über", "unter", "durch", "werden",
    "wurde", "haben", "kann", "muss", "soll", "dass", "wenn", "aber", "warum", "dann", "alle",
    "alles", "immer", "mehr", "with", "from", "this", "that", "when", "what",
];

/// Einfacher Stamm, immer ein Wortanfang: „Zertifikate“ → „zertifikat“, „Druckern“ → „druck“.
fn word_form_stem(term: &str) -> &str {
    let chars = term.chars().count();
    if chars < MIN_WORD_FORM_INPUT_CHARS {
        return term;
    }
    WORD_FORM_SUFFIXES
        .iter()
        .find(|s| term.ends_with(*s) && chars - s.chars().count() >= MIN_WORD_FORM_STEM_CHARS)
        .map_or(term, |s| &term[..term.len() - s.len()])
}

/// Präfixsuche nach Wortstämmen im Volltextindex (`"stamm"*`). Der Index entfernt Akzente,
/// daher gilt das auch für Suchtext und Einträge mit und ohne Akzent.
fn word_form_expression(terms: &[String]) -> String {
    let mut stems: Vec<&str> = Vec::new();
    for term in terms {
        if term.chars().count() < MIN_WORD_FORM_INPUT_CHARS
            || WORD_FORM_STOP_WORDS.contains(&term.as_str())
        {
            continue;
        }
        let stem = word_form_stem(term);
        if !stems.contains(&stem) {
            stems.push(stem);
        }
    }
    stems
        .iter()
        .map(|s| format!("\"{s}\"*"))
        .collect::<Vec<_>>()
        .join(" OR ")
}

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
    /// Persistent filesystem filename, including names resembling a SQLite URI.
    pub fn open_file(path: impl AsRef<Path>) -> Result<Self> {
        Self::open(literal_file_path(path)?)
    }
    /// SQLite-compatible API, including explicitly chosen :memory: and file: URIs.
    /// For persistent filenames use open_file; CLI commands always use file APIs.
    pub fn open(path: impl AsRef<Path>) -> Result<Self> {
        create_private(path.as_ref())?;
        Self::from_connection(Connection::open(path)?)
    }
    /// Öffnet nur eine vorhandene Datei, verhindert versehentliche neue Datenbanken bei Tippfehlern.
    pub fn open_existing(path: impl AsRef<Path>) -> Result<Self> {
        Self::from_connection(Connection::open_with_flags(
            literal_file_path(path)?,
            OpenFlags::SQLITE_OPEN_READ_WRITE,
        )?)
    }
    /// Reads only an existing current-schema database; never creates or upgrades.
    pub fn open_read_only(path: impl AsRef<Path>) -> Result<Self> {
        let conn = Connection::open_with_flags(
            literal_file_path(path)?,
            OpenFlags::SQLITE_OPEN_READ_ONLY,
        )?;
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
    /// Schreibt nur in eine vorhandene Datenbank mit aktuellem Schema; legt nichts an
    /// und stellt nichts um. Für Hintergrundaufrufe wie Hooks, die kein Upgrade auslösen
    /// dürfen.
    pub fn open_current(path: impl AsRef<Path>) -> Result<Self> {
        let conn = Connection::open_with_flags(
            literal_file_path(path)?,
            OpenFlags::SQLITE_OPEN_READ_WRITE,
        )?;
        conn.busy_timeout(std::time::Duration::from_secs(5))?;
        conn.pragma_update(None, "foreign_keys", true)?;
        let version: i64 = conn.query_row("PRAGMA user_version", [], |r| r.get(0))?;
        if version != SCHEMA_VERSION {
            return Err(invalid(
                "Datenbank hat nicht das aktuelle Schema; zuerst doctor, backup und ein bewusstes Upgrade ausführen",
            ));
        }
        Ok(Self { conn })
    }
    /// Kürzere Wartezeit bei gesperrter Datenbank, etwa für Hooks, die nicht blockieren dürfen.
    pub fn set_busy_timeout(&self, wait: std::time::Duration) -> Result<()> {
        self.conn.busy_timeout(wait)
    }
    /// Keeps several reads in one consistent SQLite snapshot. The callback must
    /// only read; use open_read_only when this must also be enforced by SQLite.
    pub fn read_snapshot<T>(&self, read: impl FnOnce(&Self) -> Result<T>) -> Result<T> {
        let tx = self
            .conn
            .is_autocommit()
            .then(|| self.conn.unchecked_transaction())
            .transpose()?;
        let result = read(self)?;
        if let Some(tx) = tx {
            tx.commit()?;
        }
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
            version = 5;
        }
        if version == 5 {
            tx.execute_batch(include_str!("../../../migrations/0006_observations.sql"))?;
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
        retry_busy(&self.conn, || {
            self.conn.execute(
            "INSERT INTO memories(scope, kind, problem, solution, source) VALUES (?1, ?2, ?3, ?4, ?5)",
            params![scope, kind, problem, solution, source])
        })?;
        Ok(self.conn.last_insert_rowid())
    }
    /// Dokumentiert eine externe Prüfung, keine automatische Wahrheitsprüfung.
    pub fn validate(&self, id: i64, reviewer: &str, evidence: &str) -> Result<bool> {
        nonblank(reviewer)?;
        nonblank(evidence)?;
        Ok(retry_busy(&self.conn, || {
            self.conn.execute(
                "UPDATE memories SET status='validated', validated_by=?2, evidence=?3
                 WHERE id=?1 AND status='pending'
                 AND NOT EXISTS(SELECT 1 FROM invalidations WHERE memory_id=?1)",
                params![id, reviewer, evidence],
            )
        })? == 1)
    }
    /// Zurückgezogene Einträge bleiben einsehbar, werden aber nicht mehr abgerufen.
    pub fn invalidate(&self, id: i64, actor: &str, reason: &str) -> Result<bool> {
        nonblank(actor)?;
        nonblank(reason)?;
        Ok(retry_busy(&self.conn, || {
            self.conn.execute(
                "INSERT INTO invalidations(memory_id, actor, reason)
                 SELECT id, ?2, ?3 FROM memories WHERE id=?1
                 AND NOT EXISTS(SELECT 1 FROM invalidations WHERE memory_id=?1)",
                params![id, actor, reason],
            )
        })? == 1)
    }
    pub fn get(&self, id: i64) -> Result<Option<Record>> {
        self.read_snapshot(|store| {
            let mut found = store.conn.query_row(
                &format!("SELECT {FIELDS} FROM memories m LEFT JOIN invalidations i ON i.memory_id=m.id WHERE m.id=?1"),
                [id], record,
            ).optional()?;
            if let Some(record) = found.as_mut() {
                record.check = store.check_evidence(id)?;
            }
            Ok(found)
        })
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
        self.recall_statuses(query, scope, limit, &["validated"])
    }
    /// Wie `recall`; danach füllen ungeprüfte aktive Einträge (`pending`) freie Plätze mit
    /// denselben Suchstufen. Validierte Treffer und ihre Reihenfolge bleiben unverändert vorn;
    /// ungeprüfte sind am Status erkennbar und nur Hinweise.
    pub fn recall_with_hints(&self, query: &str, scope: &str, limit: usize) -> Result<Vec<Record>> {
        self.recall_statuses(query, scope, limit, &["validated", "pending"])
    }
    fn recall_statuses(
        &self,
        query: &str,
        scope: &str,
        limit: usize,
        statuses: &[&str],
    ) -> Result<Vec<Record>> {
        nonblank(scope)?;
        if query.chars().count() > 2000 {
            return Err(invalid("Suchtext zu lang"));
        }
        if !(1..=20).contains(&limit) {
            return Err(invalid("Limit muss 1 bis 20 sein"));
        }
        let terms = search_terms(query);
        self.read_snapshot(|store| {
            let mut found = Vec::new();
            for status in statuses {
                store.recall_stages(&terms, scope, limit, status, &mut found)?;
            }
            store.enrich_records(found)
        })
    }
    /// Die drei Suchstufen für einen Status; jede füllt nur noch freie Plätze, ohne Duplikate.
    fn recall_stages(
        &self,
        terms: &[String],
        scope: &str,
        limit: usize,
        status: &str,
        found: &mut Vec<Record>,
    ) -> Result<()> {
        let partial = match_expression(
            terms
                .iter()
                .filter(|t| t.chars().count() >= MIN_PARTIAL_TERM_CHARS),
        );
        // Ganze Wörter, dann Teilwörter, dann Wortformen; bisherige Treffer bleiben vorn.
        let stages = [
            ("memories_fts", match_expression(terms.iter())),
            ("memories_trigram", partial),
            ("memories_fts", word_form_expression(terms)),
        ];
        for (index, expression) in &stages {
            if found.len() >= limit {
                break;
            }
            for extra in self.ranked(index, expression, scope, limit, status)? {
                if found.len() == limit {
                    break;
                }
                if !found.iter().any(|r| r.id == extra.id) {
                    found.push(extra);
                }
            }
        }
        Ok(())
    }
    /// Aktive Treffer eines Status aus einem FTS-Index im Bereich plus global, nach BM25.
    fn ranked(
        &self,
        index: &str,
        expression: &str,
        scope: &str,
        limit: usize,
        status: &str,
    ) -> Result<Vec<Record>> {
        if expression.is_empty() {
            return Ok(Vec::new());
        }
        let mut stmt = self.conn.prepare(&format!(
            "SELECT {FIELDS}
            FROM {index} JOIN memories m ON m.id={index}.rowid
            LEFT JOIN invalidations i ON i.memory_id=m.id
            WHERE {index} MATCH ?1 AND m.status=?4 AND i.memory_id IS NULL
            AND m.scope IN ('global', ?2)
            ORDER BY bm25({index}, 2.0, 1.0), m.id LIMIT ?3"
        ))?;
        stmt.query_map(params![expression, scope, limit as i64, status], record)?
            .collect()
    }
    pub fn pending(&self, scope: &str) -> Result<Vec<Record>> {
        nonblank(scope)?;
        self.read_snapshot(|store| {
            let mut stmt = store.conn.prepare(&format!(
                "SELECT {FIELDS} FROM memories m
            LEFT JOIN invalidations i ON i.memory_id=m.id
            WHERE m.status='pending' AND i.memory_id IS NULL AND m.scope IN ('global', ?1)
            ORDER BY m.id LIMIT 100"
            ))?;
            let records = stmt
                .query_map([scope], record)?
                .collect::<Result<Vec<_>>>()?;
            store.enrich_records(records)
        })
    }
    /// Validierte aktive Einträge im Bereich plus global, neueste zuerst.
    pub fn validated(&self, scope: &str, limit: usize) -> Result<Vec<Record>> {
        nonblank(scope)?;
        if !(1..=100).contains(&limit) {
            return Err(invalid("Limit muss 1 bis 100 sein"));
        }
        self.read_snapshot(|store| {
            let mut stmt = store.conn.prepare(&format!(
                "SELECT {FIELDS} FROM memories m
            LEFT JOIN invalidations i ON i.memory_id=m.id
            WHERE m.status='validated' AND i.memory_id IS NULL AND m.scope IN ('global', ?1)
            ORDER BY m.id DESC LIMIT ?2"
            ))?;
            let records = stmt
                .query_map(params![scope, limit as i64], record)?
                .collect::<Result<Vec<_>>>()?;
            store.enrich_records(records)
        })
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
