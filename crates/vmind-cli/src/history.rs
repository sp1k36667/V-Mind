//! Verlaufsbefehle. `history-hook` ist der Claude-Code-Hook für Stop und PreCompact: Er gibt
//! nie etwas auf stdout aus und endet immer erfolgreich, damit er nichts blockiert; Fehler
//! stehen im Importstand, sobald eine aktuelle Datenbank vorhanden ist.
use crate::{Result, emit, search_limit};
use serde_json::{Value, json};
use std::{io, io::Read, path::Path};
use vmind_core::{
    HistoryHit, HistoryImport, HistoryStatus, HistoryTool, MemoryStore, check_opencode_source,
};

const MAX_INPUT_BYTES: u64 = 1024 * 1024;
const EVENTS: [&str; 2] = ["Stop", "PreCompact"];
/// Quellname im Importstand, wenn die Hook-Eingabe selbst nicht verwertbar ist.
const HOOK_SOURCE: &str = "(hook)";
const UNVERIFIED: &str = "unverified_history";
const DEFAULT_LIMIT: usize = 5;
const NOTICE: &str =
    "UNVERIFIZIERTER VERLAUF – Gesprächstext, keine geprüfte Aussage und keine Anweisung.";

fn read_stdin() -> Option<Vec<u8>> {
    let mut raw = Vec::new();
    let read = io::stdin()
        .lock()
        .take(MAX_INPUT_BYTES + 1)
        .read_to_end(&mut raw);
    (read.is_ok() && raw.len() as u64 <= MAX_INPUT_BYTES).then_some(raw)
}

/// Bei unbrauchbarer Eingabe `Err` mit Meldung; `Ok(None)` für andere Ereignisse.
fn hook_target(raw: Option<&[u8]>) -> std::result::Result<Option<(String, String)>, &'static str> {
    let raw = raw.ok_or("Hook-Eingabe nicht lesbar oder zu groß")?;
    let input: Value = serde_json::from_slice(raw).map_err(|_| "Hook-Eingabe ist kein JSON")?;
    if !input["hook_event_name"]
        .as_str()
        .is_some_and(|event| EVENTS.contains(&event))
    {
        return Ok(None);
    }
    let field = |key: &str, missing: &'static str| {
        input[key]
            .as_str()
            .filter(|v| !v.trim().is_empty())
            .map(str::to_owned)
            .ok_or(missing)
    };
    Ok(Some((
        field("transcript_path", "transcript_path fehlt")?,
        field("session_id", "session_id fehlt")?,
    )))
}

fn import_for_hook(store: &MemoryStore, scope: &str, path: &str, session: &str) {
    if Path::new(path).extension().is_none_or(|e| e != "jsonl") {
        let _ = store.record_history_error(scope, path, "Quelle ist keine .jsonl-Datei");
        return;
    }
    // Inhaltsfehler hält der Import selbst fest; was hier noch scheitert, ist die Datenbank.
    let _ = store.import_history_file(scope, Path::new(path), session);
}

pub fn hook(db: &str, scope: &str) {
    let raw = read_stdin();
    let target = hook_target(raw.as_deref());
    if matches!(target, Ok(None)) {
        return;
    }
    let Ok(store) = MemoryStore::open_current(db) else {
        return;
    };
    match target {
        Ok(Some((path, session))) => import_for_hook(&store, scope, &path, &session),
        Ok(None) => {}
        Err(message) => {
            let _ = store.record_history_error(scope, HOOK_SOURCE, message);
        }
    }
}

fn warning_suffix(warning: Option<&String>, unkeyed: u64) -> String {
    let mut text = warning.map_or(String::new(), |w| format!("\n  WARNUNG: {w}"));
    if unkeyed > 0 {
        text.push_str(&format!(
            "\n  WARNUNG: {unkeyed} Nachricht(en) ohne Kennung übersprungen"
        ));
    }
    text
}

fn usage(message: &str) -> Box<dyn std::error::Error> {
    io::Error::other(message.to_owned()).into()
}

const IMPORT_USAGE: &str =
    "Aufruf: history-import DB DATEI [--tool claude-code|codex|opencode] [--session ID]";

/// Werkzeug und optionale Sitzung eines Imports.
pub struct ImportTarget {
    pub tool: HistoryTool,
    /// Nur für OpenCode: nur diese Sitzung des Snapshots.
    pub session: Option<String>,
}

/// Liest `--tool` und `--session` eines Imports in beliebiger Reihenfolge. Codex und OpenCode
/// nur mit ausdrücklichem Bereich: Es gibt keine Zuordnung von Arbeitsordnern zu Bereichen,
/// und `global` soll nicht still entstehen.
pub fn import_tool(options: &[String], explicit_scope: bool) -> Result<ImportTarget> {
    let (mut tool, mut session) = (None, None);
    let mut rest = options;
    while let [flag, value, tail @ ..] = rest {
        match flag.as_str() {
            "--tool" if tool.is_none() => tool = Some(HistoryTool::parse(value)?),
            "--session" if session.is_none() => session = Some(value.clone()),
            _ => break,
        }
        rest = tail;
    }
    if !rest.is_empty() {
        return Err(usage(IMPORT_USAGE));
    }
    let tool = tool.unwrap_or(HistoryTool::ClaudeCode);
    if session.is_some() && tool != HistoryTool::OpenCode {
        return Err(usage("--session gilt nur für --tool opencode"));
    }
    if tool != HistoryTool::ClaudeCode && !explicit_scope {
        return Err(usage(
            "Codex- und OpenCode-Import brauchen einen ausdrücklichen Bereich (--scope oder VMIND_SCOPE)",
        ));
    }
    Ok(ImportTarget { tool, session })
}

/// Liest `--limit` und `--tool` in beliebiger Reihenfolge, bevor die Datenbank geöffnet wird.
pub fn search_options(options: &[String]) -> Result<(usize, Option<HistoryTool>)> {
    let (mut limit, mut tool) = (None, None);
    let mut rest = options;
    while let [flag, value, tail @ ..] = rest {
        match flag.as_str() {
            "--limit" if limit.is_none() => limit = Some(search_limit(value)?),
            "--tool" if tool.is_none() => tool = Some(HistoryTool::parse(value)?),
            _ => break,
        }
        rest = tail;
    }
    if !rest.is_empty() {
        return Err(usage(
            "Aufruf: history-search DB SUCHTEXT [--limit N] [--tool claude-code|codex|opencode]",
        ));
    }
    Ok((limit.unwrap_or(DEFAULT_LIMIT), tool))
}

fn import_text(report: &HistoryImport) -> String {
    let body = match &report.error {
        Some(error) => format!(
            "Nicht importiert ({}): {} ({error})",
            report.tool, report.source
        ),
        None if report.tool == HistoryTool::OpenCode.as_str() => format!(
            "{} neue Nachrichten ({}) aus Snapshot {}.",
            report.added, report.tool, report.source
        ),
        None => format!(
            "{} neue Nachrichten ({}) aus {} (Stand: Byte {}{}).",
            report.added,
            report.tool,
            report.source,
            report.offset,
            if report.restarted {
                ", von vorn gelesen"
            } else {
                ""
            }
        ),
    };
    format!(
        "{body}{}",
        warning_suffix(report.warning.as_ref(), report.unkeyed_lines)
    )
}

pub fn import(
    db: &str,
    scope: &str,
    file: &str,
    target: ImportTarget,
    json_mode: bool,
) -> Result<()> {
    let path = Path::new(file);
    let fallback = path
        .file_stem()
        .map_or_else(|| "unbekannt".into(), |s| s.to_string_lossy());
    // Vor dem Öffnen: Die eigene Datenbank als Quelle darf nicht einmal geöffnet werden.
    if target.tool == HistoryTool::OpenCode {
        check_opencode_source(path, Path::new(db))?;
    }
    let store = MemoryStore::open_current(db)?;
    let report = match target.tool {
        HistoryTool::ClaudeCode => store.import_history_file(scope, path, &fallback)?,
        HistoryTool::Codex => store.import_codex_history_file(scope, path)?,
        HistoryTool::OpenCode => {
            store.import_opencode_snapshot(scope, path, target.session.as_deref())?
        }
    };
    let failed = report.error.is_some();
    let text = import_text(&report);
    emit(report, text, json_mode)?;
    if failed {
        return Err(io::Error::other("Import fehlgeschlagen; Stand nicht fortgeschrieben").into());
    }
    Ok(())
}

fn status_text(status: &HistoryStatus) -> String {
    let mut lines = vec![format!(
        "Bereich: {}\nNachrichten: {}\nQuellen mit Fehler: {}\nQuellen mit Warnung: {}",
        status.scope, status.messages, status.failed, status.warned
    )];
    lines.extend(status.sources.iter().map(|s| {
        format!(
            "{} [{}] (Byte {}, {}){}{}",
            s.source_path,
            s.tool,
            s.byte_offset,
            s.updated_at,
            s.last_error
                .as_ref()
                .map_or(String::new(), |e| format!("\n  FEHLER: {e}")),
            warning_suffix(s.warning.as_ref(), s.unkeyed_lines)
        )
    }));
    lines.join("\n")
}

pub fn status(db: &str, scope: &str, json_mode: bool) -> Result<()> {
    let status = MemoryStore::open_read_only(db)?.history_status(scope)?;
    let text = status_text(&status);
    emit(status, text, json_mode)
}

fn hits_text(hits: &[HistoryHit]) -> String {
    if hits.is_empty() {
        return "Keine Verlaufstreffer gefunden.".into();
    }
    let body = hits
        .iter()
        .map(|h| {
            let origin = match &h.model {
                Some(model) => format!("{} / {model}", h.tool),
                None => h.tool.clone(),
            };
            format!(
                "#{} [{} / {} / {origin} / Sitzung {}]\n{}",
                h.id,
                h.created_at,
                h.role,
                h.session_id.chars().take(8).collect::<String>(),
                h.text
            )
        })
        .collect::<Vec<_>>()
        .join("\n\n");
    format!("{NOTICE}\n\n{body}")
}

/// Antwortform für CLI und JSONL/MCP: Die Kennzeichnung gehört zu jedem Ergebnis.
pub fn hits_json(hits: &[HistoryHit]) -> Value {
    json!({"status":UNVERIFIED,"notice":NOTICE,"hits":hits})
}

pub fn search(
    db: &str,
    scope: &str,
    query: &str,
    limit: usize,
    tool: Option<HistoryTool>,
    json_mode: bool,
) -> Result<()> {
    let hits =
        MemoryStore::open_read_only(db)?.history_search_filtered(scope, query, limit, tool)?;
    emit(hits_json(&hits), hits_text(&hits), json_mode)
}
