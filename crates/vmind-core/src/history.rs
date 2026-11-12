//! Automatisch übernommener Gesprächsverlauf einer KI aus den JSONL-Dateien von Claude Code
//! und, nur per ausdrücklichem Import, von Codex (`history/codex.rs`). Dieses Format ist keine offizielle Schnittstelle: Eine unbekannte Struktur
//! wird als Fehler im Importstand festgehalten, statt still übersprungen zu werden. Nur eine
//! abgeschlossene Zeile mit ungültigem JSON wird übersprungen und als Warnung gezählt.
//!
//! Übernommen wird nur der Text von Nutzer- und Assistentennachrichten; Werkzeugaufrufe,
//! Werkzeugergebnisse, Denkblöcke sowie Meta- und Sidechain-Zeilen nie. Bekannte
//! Geheimnisformate werden vor dem Speichern ersetzt. Vom System in Nutzertext eingefügte
//! `<system-reminder>`-Blöcke werden vorher entfernt. Verlauf ist kein Prüfnachweis.
mod codex;
mod note;

use note::ImportNote;

use crate::{MemoryStore, invalid, is_busy, retry_busy, search_terms, secrets};
use rusqlite::{OptionalExtension, Result, Transaction, TransactionBehavior, params};
use serde::Serialize;
use serde_json::Value;
use std::{
    borrow::Cow,
    fs::File,
    io::{self, BufRead, BufReader, Read, Seek, SeekFrom},
    path::Path,
};

/// Längere Nachrichten werden abgeschnitten und markiert.
const MAX_TEXT_CHARS: usize = 8000;
const CUT_MARK: &str = " [gekürzt]";
const SYSTEM_BLOCK_OPEN: &str = "<system-reminder>";
const SYSTEM_BLOCK_CLOSE: &str = "</system-reminder>";
/// Schutz vor unbegrenztem Speicherbedarf; echte Zeilen mit großen Anhängen bleiben darunter.
const MAX_LINE_BYTES: u64 = 64 * 1024 * 1024;
const MAX_SCOPE_CHARS: usize = 128;
const MAX_ID_CHARS: usize = 200;
const MAX_TIMESTAMP_CHARS: usize = 64;
const MAX_PATH_CHARS: usize = 4096;
const MAX_ERROR_CHARS: usize = 1000;
/// Eine Warnung steht in `last_error`, damit kein neues Schema nötig ist: nur die Warnung, nur
/// ein Fehler oder beides mit Trennzeichen. Nach außen sind beide getrennte Felder.
const WARNING_PREFIX: &str = "Warnung: ";
const ERROR_SEPARATOR: &str = " | Fehler: ";
const MAX_LISTED_SOURCES: i64 = 100;
const MAX_QUERY_CHARS: usize = 2000;
/// Zeilen mit einem dieser Felder auf `true` sind kein eigentliches Gespräch.
const SKIP_FLAGS: [&str; 5] = [
    "isMeta",
    "isSidechain",
    "isCompactSummary",
    "isVisibleInTranscriptOnly",
    "isApiErrorMessage",
];

const CLAUDE_CODE: &str = "claude-code";
const CODEX: &str = "codex";
/// Kein echtes Modell: So kennzeichnet Claude Code selbst erzeugte Zeilen.
const SYNTHETIC_MODEL: &str = "<synthetic>";

/// Herkunft eines Verlaufs. Bildet zugleich den Namensraum für Nachrichten und Importstand.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HistoryTool {
    ClaudeCode,
    Codex,
}

impl HistoryTool {
    pub fn parse(name: &str) -> Result<Self> {
        match name {
            CLAUDE_CODE => Ok(Self::ClaudeCode),
            CODEX => Ok(Self::Codex),
            _ => Err(invalid(
                "Unbekanntes Werkzeug: erlaubt sind claude-code und codex",
            )),
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::ClaudeCode => CLAUDE_CODE,
            Self::Codex => CODEX,
        }
    }
}

/// Ergebnis eines Importlaufs. `error` ist gesetzt, wenn die Datei nicht fortgeschrieben wurde.
#[derive(Debug, Serialize)]
pub struct HistoryImport {
    pub tool: String,
    pub source: String,
    pub added: usize,
    pub offset: u64,
    /// Die Datei war kürzer als der gespeicherte Stand und wurde von vorn gelesen.
    pub restarted: bool,
    pub error: Option<String>,
    /// Bisher übersprungene beschädigte Zeilen dieser Quelle.
    pub corrupt_lines: u64,
    pub warning: Option<String>,
    /// Bisher übersprungene Nachrichten ohne `item.id` und ohne `ordinal` (nur Codex).
    pub unkeyed_lines: u64,
}

#[derive(Debug, Serialize)]
pub struct HistoryHit {
    pub id: i64,
    pub scope: String,
    pub tool: String,
    /// Nur bei belegter Zuordnung gesetzt.
    pub model: Option<String>,
    pub session_id: String,
    pub uuid: String,
    pub role: String,
    pub text: String,
    pub created_at: String,
    /// Immer `unverified`: Verlauf ist Gesprächstext, kein geprüftes Wissen.
    pub status: &'static str,
}

#[derive(Debug, Serialize)]
pub struct HistorySource {
    pub tool: String,
    pub source_path: String,
    pub byte_offset: i64,
    pub last_error: Option<String>,
    pub corrupt_lines: u64,
    pub warning: Option<String>,
    pub unkeyed_lines: u64,
    pub updated_at: String,
}

#[derive(Debug, Serialize)]
pub struct HistoryStatus {
    pub scope: String,
    pub messages: i64,
    pub failed: i64,
    /// Quellen mit übersprungenen beschädigten Zeilen oder Nachrichten ohne Kennung.
    pub warned: i64,
    /// Neueste zuerst, höchstens 100.
    pub sources: Vec<HistorySource>,
}

struct Message {
    session_id: String,
    uuid: String,
    role: &'static str,
    text: String,
    created_at: String,
    model: Option<String>,
    /// Nur während des Lesens: Schlüssel für die Modellzuordnung.
    turn_id: Option<String>,
}

enum LineOutcome {
    Skip,
    Message(Message),
    /// Nachricht ohne verwertbare Kennung; wird nur gezählt.
    Unkeyed,
}

/// Zeilendeutung je Werkzeug; das Lesen der Datei und das Speichern sind gemeinsam.
enum Adapter<'a> {
    Claude(&'a str),
    Codex(codex::Cursor),
}

impl Adapter<'_> {
    fn parse(&mut self, row: &Value) -> std::result::Result<LineOutcome, &'static str> {
        match self {
            Self::Claude(fallback) => Ok(match parse_row(row, fallback)? {
                Some(message) => LineOutcome::Message(message),
                None => LineOutcome::Skip,
            }),
            Self::Codex(cursor) => cursor.parse(row),
        }
    }

    fn restart(&mut self) {
        if let Self::Codex(cursor) = self {
            *cursor = codex::Cursor::default();
        }
    }
}

/// In diesem Lauf übersprungene Zeilen; enthält bewusst keine Zeileninhalte.
struct CorruptLines {
    count: u64,
    last_byte: u64,
}

struct Batch {
    messages: Vec<Message>,
    end: u64,
    restarted: bool,
    corrupt: Option<CorruptLines>,
    unkeyed: u64,
    cursor: Option<codex::Cursor>,
}

/// Gespeicherter Stand einer Quelle.
#[derive(Default)]
struct Progress {
    offset: u64,
    unkeyed: u64,
    session: Option<String>,
    turn: Option<String>,
    model: Option<String>,
}

fn bounded_id(value: &str, max: usize) -> bool {
    !value.trim().is_empty() && value.chars().count() <= max && !value.chars().any(char::is_control)
}

fn check_scope(scope: &str) -> Result<()> {
    if bounded_id(scope, MAX_SCOPE_CHARS) {
        Ok(())
    } else {
        Err(invalid("Ungültiger Bereich"))
    }
}

/// Textteile der Nachricht; alles außer Textblöcken wird nicht übernommen.
fn message_text(content: &Value) -> std::result::Result<String, &'static str> {
    match content {
        Value::String(text) => Ok(text.clone()),
        Value::Array(blocks) => {
            let mut parts = Vec::new();
            for block in blocks {
                let kind = block["type"]
                    .as_str()
                    .ok_or("Inhaltsblock ohne Typ oder kein Objekt")?;
                if kind == "text" {
                    parts.push(block["text"].as_str().ok_or("Textblock ohne Text")?);
                }
            }
            Ok(parts.join("\n"))
        }
        _ => Err("Inhalt ist weder Text noch Blockliste"),
    }
}

fn required_id<'a>(
    row: &'a Value,
    key: &str,
    max: usize,
    missing: &'static str,
) -> std::result::Result<&'a str, &'static str> {
    row[key]
        .as_str()
        .filter(|v| bounded_id(v, max))
        .ok_or(missing)
}

/// Entfernt vom System eingefügte Blöcke aus Nutzertext und trimmt dann den Rand. Text ohne
/// Tag bleibt exakt erhalten. Unvollständige Blöcke hinterlassen keine Teilinhalte: Ohne Ende
/// fällt alles ab dem öffnenden Tag weg, ohne Anfang alles seit dem letzten Block bis zum Ende.
fn without_system_blocks(text: &str) -> Cow<'_, str> {
    if !text.contains(SYSTEM_BLOCK_OPEN) && !text.contains(SYSTEM_BLOCK_CLOSE) {
        return Cow::Borrowed(text);
    }
    let mut kept = String::new();
    let mut text_start = 0;
    let mut depth = 0usize;
    for (at, _) in text.match_indices('<') {
        let rest = &text[at..];
        if rest.starts_with(SYSTEM_BLOCK_OPEN) {
            if depth == 0 {
                kept.push_str(&text[text_start..at]);
            }
            depth += 1;
        } else if rest.starts_with(SYSTEM_BLOCK_CLOSE) {
            depth = depth.saturating_sub(1);
            if depth == 0 {
                text_start = at + SYSTEM_BLOCK_CLOSE.len();
            }
        }
    }
    if depth == 0 {
        kept.push_str(&text[text_start..]);
    }
    Cow::Owned(kept.trim().to_owned())
}

/// Erst redigieren, dann kürzen: Ein angeschnittenes Geheimnis wäre nicht mehr erkennbar.
fn stored_text(raw: &str) -> String {
    let clean = secrets::redact(raw);
    if clean.chars().count() <= MAX_TEXT_CHARS {
        return clean;
    }
    let mut cut: String = clean.chars().take(MAX_TEXT_CHARS).collect();
    cut.push_str(CUT_MARK);
    cut
}

/// Während eines Turns gesendete Nutzernachricht. Unterschieden wird nur an den Feldern
/// `commandMode`, `origin.kind` und `isMeta`: Benachrichtigungen, Nachrichten anderer
/// Absender und sonstige Anhänge bleiben draußen, auch bei unbekannten Werten.
fn queued_user_text(row: &Value) -> std::result::Result<Option<String>, &'static str> {
    let attachment = &row["attachment"];
    if attachment["type"].as_str() != Some("queued_command")
        || attachment["commandMode"].as_str() != Some("prompt")
        || attachment["origin"]["kind"].as_str() != Some("human")
    {
        return Ok(None);
    }
    match attachment.get("isMeta") {
        None | Some(Value::Bool(false)) => message_text(&attachment["prompt"]).map(Some),
        Some(Value::Bool(true)) => Ok(None),
        Some(_) => Err("Kennzeichen ist kein Wahrheitswert"),
    }
}

/// Modell einer Assistentenzeile, wenn es dort gültig steht. Sonst `None`: Das Feld ist nur
/// Zusatzwissen und darf den bestehenden Import nie anhalten.
fn claude_model(row: &Value, role: &str) -> Option<String> {
    if role != "assistant" {
        return None;
    }
    row["message"]["model"]
        .as_str()
        .filter(|m| *m != SYNTHETIC_MODEL && bounded_id(m, MAX_ID_CHARS))
        .map(str::to_owned)
}

/// `Ok(None)` für Zeilen ohne übernehmbaren Text; `Err` für eine unbekannte Struktur.
fn parse_row(row: &Value, fallback: &str) -> std::result::Result<Option<Message>, &'static str> {
    if !row.is_object() {
        return Err("Zeile ist kein JSON-Objekt");
    }
    let (role, queued) = match row["type"].as_str() {
        None => return Err("Zeile ohne Typ"),
        Some("user") => ("user", None),
        Some("assistant") => ("assistant", None),
        Some("attachment") => match queued_user_text(row)? {
            Some(text) => ("user", Some(text)),
            None => return Ok(None),
        },
        // Andere Zeilentypen (Metadaten, Abrechnung …) enthalten kein Gespräch.
        Some(_) => return Ok(None),
    };
    for flag in SKIP_FLAGS {
        match row.get(flag) {
            None | Some(Value::Bool(false)) => {}
            Some(Value::Bool(true)) => return Ok(None),
            Some(_) => return Err("Kennzeichen ist kein Wahrheitswert"),
        }
    }
    let uuid = required_id(row, "uuid", MAX_ID_CHARS, "uuid fehlt oder ist ungültig")?;
    let created_at = required_id(
        row,
        "timestamp",
        MAX_TIMESTAMP_CHARS,
        "timestamp fehlt oder ist ungültig",
    )?;
    let session_id = match &row["sessionId"] {
        Value::Null => fallback,
        Value::String(session) => session,
        _ => return Err("sessionId ist kein Text"),
    };
    if !bounded_id(session_id, MAX_ID_CHARS) {
        return Err("Sitzungskennung ungültig");
    }
    let text = match queued {
        Some(text) => text,
        None => {
            let message = &row["message"];
            if message["role"].as_str() != Some(role) {
                return Err("message.role passt nicht zum Zeilentyp");
            }
            message_text(&message["content"])?
        }
    };
    let text = if role == "user" {
        without_system_blocks(&text)
    } else {
        Cow::Borrowed(text.as_str())
    };
    if text.trim().is_empty() {
        return Ok(None);
    }
    Ok(Some(Message {
        session_id: session_id.to_owned(),
        uuid: uuid.to_owned(),
        role,
        text: stored_text(&text),
        created_at: created_at.to_owned(),
        model: claude_model(row, role),
        turn_id: None,
    }))
}

fn io_message(what: &str, error: &io::Error) -> String {
    format!("{what}: {}", error.kind())
}

/// Liest alle vollständigen Zeilen ab dem Stand; abgeschlossene Zeilen mit ungültigem JSON
/// werden nur gezählt. Fehlermeldungen und Warnungen enthalten nie Zeileninhalte.
fn read_new_lines(
    path: &Path,
    stored: u64,
    mut adapter: Adapter<'_>,
) -> std::result::Result<Batch, String> {
    // Vor dem Öffnen prüfen: Das Öffnen einer FIFO würde den Hook blockieren.
    let meta = std::fs::metadata(path).map_err(|e| io_message("Datei nicht lesbar", &e))?;
    if !meta.is_file() {
        return Err("Quelle ist keine reguläre Datei".into());
    }
    let restarted = meta.len() < stored;
    let start = if restarted { 0 } else { stored };
    if restarted {
        adapter.restart();
    }
    let mut file = File::open(path).map_err(|e| io_message("Datei nicht lesbar", &e))?;
    file.seek(SeekFrom::Start(start))
        .map_err(|e| io_message("Datei nicht lesbar", &e))?;
    let mut reader = BufReader::new(file);
    let mut messages = Vec::new();
    let mut corrupt: Option<CorruptLines> = None;
    let mut unkeyed = 0;
    let mut end = start;
    let mut line = Vec::new();
    loop {
        line.clear();
        let read = Read::by_ref(&mut reader)
            .take(MAX_LINE_BYTES + 1)
            .read_until(b'\n', &mut line)
            .map_err(|e| io_message("Datei nicht lesbar", &e))?;
        if read as u64 > MAX_LINE_BYTES {
            return Err(format!(
                "Zeile ab Byte {end} überschreitet die Größengrenze"
            ));
        }
        // Dateiende oder halb geschriebene letzte Zeile: beim nächsten Lauf erneut lesen.
        if line.last() != Some(&b'\n') {
            break;
        }
        if !line.trim_ascii().is_empty() {
            match serde_json::from_slice::<Value>(&line) {
                Ok(value) => {
                    let unknown = |why: &str| format!("Unbekannte Struktur ab Byte {end}: {why}");
                    match adapter.parse(&value).map_err(unknown)? {
                        LineOutcome::Skip => {}
                        LineOutcome::Message(message) => messages.push(message),
                        LineOutcome::Unkeyed => unkeyed += 1,
                    }
                }
                Err(_) => {
                    corrupt = Some(CorruptLines {
                        count: corrupt.map_or(0, |c| c.count) + 1,
                        last_byte: end,
                    });
                }
            }
        }
        end += read as u64;
    }
    let cursor = match adapter {
        Adapter::Claude(_) => None,
        Adapter::Codex(cursor) => {
            cursor.assign_models(&mut messages);
            Some(cursor)
        }
    };
    Ok(Batch {
        messages,
        end,
        restarted,
        corrupt,
        unkeyed,
        cursor,
    })
}

fn clipped(text: &str, max: usize) -> String {
    text.chars().take(max).collect()
}

impl MemoryStore {
    fn history_progress(&self, tool: HistoryTool, scope: &str, source: &str) -> Result<Progress> {
        let progress = self
            .conn
            .query_row(
                "SELECT byte_offset, unkeyed_lines, session_id, last_turn_id, last_model
                 FROM history_imports WHERE scope=?1 AND tool=?2 AND source_path=?3",
                params![scope, tool.as_str(), source],
                |r| {
                    Ok(Progress {
                        offset: r.get::<_, i64>(0)?.max(0) as u64,
                        unkeyed: r.get::<_, i64>(1)?.max(0) as u64,
                        session: r.get(2)?,
                        turn: r.get(3)?,
                        model: r.get(4)?,
                    })
                },
            )
            .optional()?;
        Ok(progress.unwrap_or_default())
    }

    fn history_note(&self, tool: HistoryTool, scope: &str, source: &str) -> Result<ImportNote> {
        let stored: Option<Option<String>> = self
            .conn
            .query_row(
                "SELECT last_error FROM history_imports
                 WHERE scope=?1 AND tool=?2 AND source_path=?3",
                params![scope, tool.as_str(), source],
                |r| r.get(0),
            )
            .optional()?;
        Ok(ImportNote::parse(stored.flatten().as_deref()))
    }

    /// Hält einen Importfehler des Claude-Code-Verlaufs fest (Hook), ohne Stand oder Warnung
    /// zu verändern.
    pub fn record_history_error(&self, scope: &str, source: &str, message: &str) -> Result<()> {
        self.record_tool_error(HistoryTool::ClaudeCode, scope, source, message)
    }

    fn record_tool_error(
        &self,
        tool: HistoryTool,
        scope: &str,
        source: &str,
        message: &str,
    ) -> Result<()> {
        check_scope(scope)?;
        let source = clipped(source, MAX_PATH_CHARS);
        let message = clipped(message, MAX_ERROR_CHARS);
        let tx = retry_busy(&self.conn, || {
            Transaction::new_unchecked(&self.conn, TransactionBehavior::Immediate)
        })?;
        let note = ImportNote {
            error: Some(message),
            ..self.history_note(tool, scope, &source)?
        };
        tx.execute(
            "INSERT INTO history_imports(scope, tool, source_path, last_error)
             VALUES(?1, ?2, ?3, ?4)
             ON CONFLICT(scope, tool, source_path) DO UPDATE SET last_error=excluded.last_error,
             updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')",
            params![scope, tool.as_str(), source, note.stored()],
        )?;
        tx.commit()
    }

    /// Schreibt Nachrichten, Stand und Warnung atomar. Hat ein paralleler Lauf den Stand inzwischen
    /// geändert, gilt dessen Ergebnis und `None` kommt zurück; die uuid verhindert Duplikate.
    fn commit_history(
        &self,
        tool: HistoryTool,
        scope: &str,
        source: &str,
        expected: u64,
        batch: &Batch,
    ) -> Result<Option<(usize, ImportNote, u64)>> {
        let tx = retry_busy(&self.conn, || {
            Transaction::new_unchecked(&self.conn, TransactionBehavior::Immediate)
        })?;
        let current = self.history_progress(tool, scope, source)?;
        if current.offset != expected {
            return Ok(None);
        }
        let note = self.history_note(tool, scope, source)?.after_batch(batch);
        let unkeyed = if batch.restarted {
            batch.unkeyed
        } else {
            current.unkeyed.saturating_add(batch.unkeyed)
        };
        let mut added = 0;
        {
            let mut insert = tx.prepare_cached(
                "INSERT INTO history_messages(scope, tool, model, session_id, uuid, role, text,
                 created_at) VALUES(?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)
                 ON CONFLICT(scope, tool, uuid) DO NOTHING",
            )?;
            for m in &batch.messages {
                added += insert.execute(params![
                    scope,
                    tool.as_str(),
                    m.model,
                    m.session_id,
                    m.uuid,
                    m.role,
                    m.text,
                    m.created_at
                ])?;
            }
        }
        let (session, (turn, model)) = match &batch.cursor {
            Some(cursor) => (cursor.session(), cursor.last_turn()),
            None => (None, (None, None)),
        };
        tx.execute(
            "INSERT INTO history_imports(scope, tool, source_path, byte_offset, last_error,
             unkeyed_lines, session_id, last_turn_id, last_model)
             VALUES(?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)
             ON CONFLICT(scope, tool, source_path) DO UPDATE SET byte_offset=excluded.byte_offset,
             last_error=excluded.last_error, unkeyed_lines=excluded.unkeyed_lines,
             session_id=excluded.session_id, last_turn_id=excluded.last_turn_id,
             last_model=excluded.last_model, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')",
            params![
                scope,
                tool.as_str(),
                source,
                batch.end as i64,
                note.stored(),
                unkeyed as i64,
                session,
                turn,
                model
            ],
        )?;
        tx.commit()?;
        Ok(Some((added, note, unkeyed)))
    }

    /// Übernimmt neue Zeilen eines Claude-Code-Transkripts ab dem gespeicherten Stand.
    /// Inhaltliche und Dateifehler landen im Importstand und in `HistoryImport::error`; dann
    /// bleibt alles unverändert.
    pub fn import_history_file(
        &self,
        scope: &str,
        path: &Path,
        fallback_session: &str,
    ) -> Result<HistoryImport> {
        self.import_source(HistoryTool::ClaudeCode, scope, path, |_| {
            Adapter::Claude(fallback_session)
        })
    }

    /// Wie `import_history_file`, aber für genau eine unkomprimierte Rollout-Datei von Codex.
    /// Die Sitzung stammt aus `session_meta`; ein Lauf ab Byte-Stand nutzt die gespeicherte.
    pub fn import_codex_history_file(&self, scope: &str, path: &Path) -> Result<HistoryImport> {
        self.import_source(HistoryTool::Codex, scope, path, |progress| {
            Adapter::Codex(codex::Cursor::resume(
                progress.session.clone(),
                progress.turn.clone(),
                progress.model.clone(),
            ))
        })
    }

    fn import_source<'a>(
        &self,
        tool: HistoryTool,
        scope: &str,
        path: &Path,
        adapter: impl FnOnce(&Progress) -> Adapter<'a>,
    ) -> Result<HistoryImport> {
        check_scope(scope)?;
        let source = path.to_string_lossy().into_owned();
        if source.chars().count() > MAX_PATH_CHARS {
            return Err(invalid("Quellpfad zu lang"));
        }
        let stored = self.history_progress(tool, scope, &source)?;
        let report = |added, offset, restarted, error, note: ImportNote, unkeyed| HistoryImport {
            tool: tool.as_str().to_owned(),
            source: source.clone(),
            added,
            offset,
            restarted,
            error,
            corrupt_lines: note.corrupt_lines,
            warning: note.warning,
            unkeyed_lines: unkeyed,
        };
        let batch = match read_new_lines(path, stored.offset, adapter(&stored)) {
            Ok(batch) => batch,
            Err(message) => {
                self.record_tool_error(tool, scope, &source, &message)?;
                let note = self.history_note(tool, scope, &source)?;
                return Ok(report(
                    0,
                    stored.offset,
                    false,
                    Some(message),
                    note,
                    stored.unkeyed,
                ));
            }
        };
        match self.commit_history(tool, scope, &source, stored.offset, &batch) {
            Ok(Some((added, note, unkeyed))) => Ok(report(
                added,
                batch.end,
                batch.restarted,
                None,
                note,
                unkeyed,
            )),
            Ok(None) => {
                let now = self.history_progress(tool, scope, &source)?;
                let note = self.history_note(tool, scope, &source)?;
                Ok(report(0, now.offset, false, None, note, now.unkeyed))
            }
            Err(error) => {
                if !is_busy(&error) {
                    let message = "Datenbankfehler beim Speichern; nichts übernommen";
                    // Der ursprüngliche Fehler zählt, auch wenn dieser Eintrag scheitert.
                    let _ = self.record_tool_error(tool, scope, &source, message);
                }
                Err(error)
            }
        }
    }

    /// Volltextsuche nur im genannten Bereich über alle Werkzeuge; siehe
    /// `history_search_filtered`.
    pub fn history_search(
        &self,
        scope: &str,
        query: &str,
        limit: usize,
    ) -> Result<Vec<HistoryHit>> {
        self.history_search_filtered(scope, query, limit, None)
    }

    /// Volltextsuche nur im genannten Bereich, optional nur für ein Werkzeug: Alle Wörter
    /// müssen vorkommen; relevanteste zuerst, bei gleicher Relevanz die neuesten.
    pub fn history_search_filtered(
        &self,
        scope: &str,
        query: &str,
        limit: usize,
        tool: Option<HistoryTool>,
    ) -> Result<Vec<HistoryHit>> {
        check_scope(scope)?;
        if query.chars().count() > MAX_QUERY_CHARS {
            return Err(invalid("Suchtext zu lang"));
        }
        if !(1..=20).contains(&limit) {
            return Err(invalid("Limit muss 1 bis 20 sein"));
        }
        let terms = search_terms(query);
        if terms.is_empty() {
            return Ok(Vec::new());
        }
        // Nur gequotete Begriffe gelangen in MATCH, keine vom Aufrufer gelieferte FTS-Syntax.
        let expression = terms
            .iter()
            .map(|t| format!("\"{t}\""))
            .collect::<Vec<_>>()
            .join(" AND ");
        let mut stmt = self.conn.prepare(
            "SELECT h.id, h.scope, h.tool, h.model, h.session_id, h.uuid, h.role, h.text,
             h.created_at
             FROM history_fts JOIN history_messages h ON h.id=history_fts.rowid
             WHERE history_fts MATCH ?1 AND h.scope=?2 AND (?4 IS NULL OR h.tool=?4)
             ORDER BY bm25(history_fts), h.created_at DESC, h.id DESC LIMIT ?3",
        )?;
        let tool = tool.map(HistoryTool::as_str);
        stmt.query_map(params![expression, scope, limit as i64, tool], |r| {
            Ok(HistoryHit {
                id: r.get(0)?,
                scope: r.get(1)?,
                tool: r.get(2)?,
                model: r.get(3)?,
                session_id: r.get(4)?,
                uuid: r.get(5)?,
                role: r.get(6)?,
                text: r.get(7)?,
                created_at: r.get(8)?,
                status: "unverified",
            })
        })?
        .collect()
    }

    /// Importstand eines Bereichs mit Fehlern; nur lesend.
    pub fn history_status(&self, scope: &str) -> Result<HistoryStatus> {
        check_scope(scope)?;
        self.read_snapshot(|store| {
            let (messages, failed, warned) = store.conn.query_row(
                "SELECT (SELECT count(*) FROM history_messages WHERE scope=?1),
                 (SELECT count(*) FROM history_imports WHERE scope=?1 AND last_error IS NOT NULL
                  AND (last_error NOT LIKE ?2 OR last_error LIKE ?3)),
                 (SELECT count(*) FROM history_imports WHERE scope=?1
                  AND (last_error LIKE ?2 OR unkeyed_lines>0))",
                params![
                    scope,
                    format!("{WARNING_PREFIX}%"),
                    format!("%{ERROR_SEPARATOR}%")
                ],
                |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
            )?;
            let mut stmt = store.conn.prepare(
                "SELECT tool, source_path, byte_offset, last_error, unkeyed_lines, updated_at
                 FROM history_imports WHERE scope=?1 ORDER BY updated_at DESC, id DESC LIMIT ?2",
            )?;
            let sources = stmt
                .query_map(params![scope, MAX_LISTED_SOURCES], |r| {
                    let note = ImportNote::parse(r.get::<_, Option<String>>(3)?.as_deref());
                    Ok(HistorySource {
                        tool: r.get(0)?,
                        source_path: r.get(1)?,
                        byte_offset: r.get(2)?,
                        last_error: note.error,
                        corrupt_lines: note.corrupt_lines,
                        warning: note.warning,
                        unkeyed_lines: r.get::<_, i64>(4)?.max(0) as u64,
                        updated_at: r.get(5)?,
                    })
                })?
                .collect::<Result<Vec<_>>>()?;
            Ok(HistoryStatus {
                scope: scope.to_owned(),
                messages,
                failed,
                warned,
                sources,
            })
        })
    }
}
