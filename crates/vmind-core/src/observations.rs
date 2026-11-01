//! Beobachtungen eines Hosts (zunächst Claude Code): welches Werkzeug lief, ob es
//! abgeschlossen oder fehlgeschlagen ist und welche Projektdateien es betraf. Nie
//! Befehle, Ausgaben, Fehlertexte oder Dateiinhalte. Beobachtet heißt nicht geprüft.
use crate::{MemoryStore, invalid};
use rusqlite::{Connection, OptionalExtension, Result, params};
use serde::Serialize;

pub(crate) const HOST: &str = "claude-code";
const TOOLS: [&str; 3] = ["Bash", "Edit", "Write"];
const RESULTS: [&str; 2] = ["completed", "failed"];
const MAX_ID_CHARS: usize = 200;
const MAX_PATH_CHARS: usize = 400;
const MAX_PATHS: usize = 20;
/// So viele Pfade zeigt eine Sitzungszusammenfassung; die Gesamtzahl steht dabei.
const SUMMARY_PATHS: usize = 5;
pub(crate) const RESUME_SESSIONS: usize = 3;

/// Ein Werkzeugaufruf, wie ihn ein Hook meldet; Pfade relativ zum Projekt.
#[derive(Debug, Clone)]
pub struct Observation {
    pub session_id: String,
    pub tool_use_id: String,
    pub tool: String,
    pub result: String,
    pub paths: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct SessionSummary {
    pub session_id: String,
    pub first_at: String,
    pub last_at: String,
    pub calls: i64,
    pub failed: i64,
    pub files: i64,
    /// Zuletzt betroffene Dateien, höchstens fünf.
    pub paths: Vec<String>,
}

fn text(value: &str, max: usize, what: &str) -> Result<()> {
    if value.trim().is_empty() || value.chars().count() > max || value.chars().any(char::is_control)
    {
        return Err(invalid(&format!("Ungültige Beobachtung: {what}")));
    }
    Ok(())
}

fn normalized_paths(paths: &[String]) -> Result<Vec<String>> {
    for p in paths {
        text(p, MAX_PATH_CHARS, "Pfad")?;
    }
    let mut out = paths.to_vec();
    out.sort();
    out.dedup();
    out.truncate(MAX_PATHS);
    Ok(out)
}

/// Zusammenfassungen der letzten Sitzungen eines Bereichs, neueste zuerst.
pub(crate) fn session_summaries(
    conn: &Connection,
    scope: &str,
    limit: usize,
) -> Result<Vec<SessionSummary>> {
    let mut stmt = conn.prepare(
        "SELECT session_id, min(created_at), max(created_at), count(*),
         count(CASE WHEN result='failed' THEN 1 END)
         FROM observations WHERE scope=?1 AND host=?2
         GROUP BY session_id ORDER BY max(id) DESC LIMIT ?3",
    )?;
    let sessions = stmt
        .query_map(params![scope, HOST, limit as i64], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get(1)?,
                r.get(2)?,
                r.get(3)?,
                r.get(4)?,
            ))
        })?
        .collect::<Result<Vec<(String, String, String, i64, i64)>>>()?;
    let mut out = Vec::new();
    for (session_id, first_at, last_at, calls, failed) in sessions {
        let files = conn.query_row(
            "SELECT count(DISTINCT p.value) FROM observations o, json_each(o.paths) p
             WHERE o.scope=?1 AND o.host=?2 AND o.session_id=?3",
            params![scope, HOST, session_id],
            |r| r.get(0),
        )?;
        let mut stmt = conn.prepare(
            "SELECT p.value FROM observations o, json_each(o.paths) p
             WHERE o.scope=?1 AND o.host=?2 AND o.session_id=?3
             GROUP BY p.value ORDER BY max(o.id) DESC LIMIT ?4",
        )?;
        let paths = stmt
            .query_map(
                params![scope, HOST, session_id, SUMMARY_PATHS as i64],
                |r| r.get(0),
            )?
            .collect::<Result<Vec<String>>>()?;
        out.push(SessionSummary {
            session_id,
            first_at,
            last_at,
            calls,
            failed,
            files,
            paths,
        });
    }
    Ok(out)
}

impl MemoryStore {
    /// Speichert eine Beobachtung genau einmal. Dieselbe Meldung erneut ergibt `false`;
    /// dieselbe ID mit anderem Inhalt oder Bereich ist ein Fehler.
    pub fn observe(&self, scope: &str, o: &Observation) -> Result<bool> {
        text(scope, 128, "Bereich")?;
        text(&o.session_id, MAX_ID_CHARS, "Sitzung")?;
        text(&o.tool_use_id, MAX_ID_CHARS, "Werkzeugaufruf")?;
        if !TOOLS.contains(&o.tool.as_str()) {
            return Err(invalid("Ungültige Beobachtung: Werkzeug nicht unterstützt"));
        }
        if !RESULTS.contains(&o.result.as_str()) {
            return Err(invalid("Ungültige Beobachtung: Ergebnis"));
        }
        let paths = serde_json::to_string(&normalized_paths(&o.paths)?)
            .map_err(|e| invalid(&e.to_string()))?;
        let inserted = self.conn.execute(
            "INSERT INTO observations(scope, host, session_id, tool_use_id, tool, result, paths)
             VALUES(?1, ?2, ?3, ?4, ?5, ?6, ?7)
             ON CONFLICT(host, session_id, tool_use_id) DO NOTHING",
            params![
                scope,
                HOST,
                o.session_id,
                o.tool_use_id,
                o.tool,
                o.result,
                paths
            ],
        )? == 1;
        if inserted {
            return Ok(true);
        }
        let same: Option<bool> = self
            .conn
            .query_row(
                "SELECT scope=?4 AND tool=?5 AND result=?6 AND paths=?7 FROM observations
                 WHERE host=?1 AND session_id=?2 AND tool_use_id=?3",
                params![
                    HOST,
                    o.session_id,
                    o.tool_use_id,
                    scope,
                    o.tool,
                    o.result,
                    paths
                ],
                |r| r.get(0),
            )
            .optional()?;
        match same {
            Some(true) => Ok(false),
            _ => Err(invalid(
                "Beobachtung mit gleicher ID, aber anderem Inhalt oder Bereich",
            )),
        }
    }
    /// Zusammenfassungen je Sitzung, neueste zuerst (höchstens 20).
    pub fn observed_sessions(&self, scope: &str, limit: usize) -> Result<Vec<SessionSummary>> {
        text(scope, 128, "Bereich")?;
        if !(1..=20).contains(&limit) {
            return Err(invalid("Limit muss 1 bis 20 sein"));
        }
        session_summaries(&self.conn, scope, limit)
    }
}
