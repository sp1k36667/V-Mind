//! Read-only evidence for the current check definition, not a truth judgement.
use crate::{MemoryStore, Record, invalid};
use rusqlite::{OptionalExtension, Result};
use serde::Serialize;

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum CheckState {
    #[default]
    None,
    NotRun,
    Passed,
    Failed,
    Error,
}

#[derive(Debug, Clone, Serialize)]
pub struct CheckVerdict {
    pub outcome: String,
    pub run_id: i64,
    pub run_at: String,
}

#[derive(Debug, Clone, Default, Serialize)]
pub struct CheckEvidence {
    pub state: CheckState,
    pub check_id: Option<i64>,
    pub run_id: Option<i64>,
    pub run_at: Option<String>,
    /// Latest passed/failed result of this definition; an execution error does not
    /// erase it. A replaced definition starts with no result, even after an old pass.
    pub last_verdict: Option<CheckVerdict>,
}

impl MemoryStore {
    /// Evidence only: does not execute anything, change status, or inspect Git.
    pub fn check_evidence(&self, memory_id: i64) -> Result<CheckEvidence> {
        self.conn
            .query_row(
                "SELECT c.id, r.id, r.outcome, r.created_at, v.id, v.outcome, v.created_at
             FROM memory_checks c
             LEFT JOIN check_runs r ON r.id=(SELECT max(id) FROM check_runs WHERE check_id=c.id)
             LEFT JOIN check_runs v ON v.id=(SELECT max(id) FROM check_runs
                                             WHERE check_id=c.id AND outcome IN ('passed','failed'))
             WHERE c.memory_id=?1 ORDER BY c.id DESC LIMIT 1",
                [memory_id],
                |row| {
                    let run_id: Option<i64> = row.get(1)?;
                    let outcome: Option<String> = row.get(2)?;
                    let state = match outcome.as_deref() {
                        None if run_id.is_none() => CheckState::NotRun,
                        Some("passed") => CheckState::Passed,
                        Some("failed") => CheckState::Failed,
                        Some("error") => CheckState::Error,
                        _ => return Err(invalid("Unbekanntes Prüfergebnis")),
                    };
                    let verdict_id: Option<i64> = row.get(4)?;
                    let last_verdict = match verdict_id {
                        Some(run_id) => Some(CheckVerdict {
                            run_id,
                            outcome: row.get(5)?,
                            run_at: row.get(6)?,
                        }),
                        None => None,
                    };
                    Ok(CheckEvidence {
                        state,
                        check_id: Some(row.get(0)?),
                        run_id,
                        run_at: row.get(3)?,
                        last_verdict,
                    })
                },
            )
            .optional()
            .map(|result| result.unwrap_or_default())
    }

    // Called only after ranking/limiting so irrelevant candidates incur no extra reads.
    pub(crate) fn enrich_records(&self, mut records: Vec<Record>) -> Result<Vec<Record>> {
        for record in &mut records {
            record.check = self.check_evidence(record.id)?;
        }
        Ok(records)
    }
}
