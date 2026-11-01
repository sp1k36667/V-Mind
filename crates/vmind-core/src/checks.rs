//! Ausführbare Prüfungen für Einträge. Der Kern führt keine Befehle aus: Er speichert
//! Prüfbefehle und Läufe und leitet daraus Statusänderungen ab.
use crate::{MemoryStore, invalid, nonblank};
use rusqlite::{OptionalExtension, Result, params, types::Type};
use serde::Serialize;

const MAX_ARGV_CHARS: usize = 4000;
const MAX_WORKDIR_CHARS: usize = 4096;
const MAX_ACTOR_CHARS: usize = 200;
const MAX_OUTPUT_CHARS: usize = 4000;
const MAX_SCOPE_CHECKS: i64 = 1000;
/// Akteur in der Historie für Statusänderungen durch Prüfläufe.
pub const CHECK_ACTOR: &str = "vmind check";

#[derive(Debug, Clone, Serialize)]
pub struct Check {
    pub id: i64,
    pub memory_id: i64,
    pub argv: Vec<String>,
    pub workdir: String,
    pub set_by: String,
    pub created_at: String,
}

#[derive(Debug, Serialize)]
pub struct CheckRun {
    pub id: i64,
    pub check_id: i64,
    pub outcome: String,
    pub exit_code: Option<i64>,
    pub duration_ms: i64,
    pub output: String,
    pub created_at: String,
}

/// `Error` heißt: Befehl nicht startbar oder Zeitlimit, also keine Aussage über den Eintrag.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Outcome {
    Passed,
    Failed,
    Error,
}

impl Outcome {
    fn as_str(self) -> &'static str {
        match self {
            Outcome::Passed => "passed",
            Outcome::Failed => "failed",
            Outcome::Error => "error",
        }
    }
}

#[derive(Debug)]
pub struct CheckResult {
    pub outcome: Outcome,
    pub exit_code: Option<i64>,
    pub duration_ms: u64,
    pub output: String,
}

#[derive(Debug, Serialize)]
pub struct Applied {
    pub memory_id: i64,
    pub check_id: i64,
    pub run_id: i64,
    pub outcome: Outcome,
    pub status_before: String,
    pub status_after: String,
}

/// Behält das Ende der Ausgabe; dort stehen bei Testläufen die Ergebnisse.
fn tail(text: &str, max: usize) -> String {
    let count = text.chars().count();
    if count <= max {
        text.into()
    } else {
        text.chars().skip(count - max).collect()
    }
}

fn check_row(row: &rusqlite::Row<'_>) -> Result<Check> {
    let raw: String = row.get(2)?;
    let argv = serde_json::from_str(&raw)
        .map_err(|e| rusqlite::Error::FromSqlConversionFailure(2, Type::Text, Box::new(e)))?;
    Ok(Check {
        id: row.get(0)?,
        memory_id: row.get(1)?,
        argv,
        workdir: row.get(3)?,
        set_by: row.get(4)?,
        created_at: row.get(5)?,
    })
}

const CHECK_FIELDS: &str = "c.id, c.memory_id, c.argv, c.workdir, c.set_by, c.created_at";

/// Setzt ein Argument für die Anzeige in einfache Anführungszeichen, wenn es Leerzeichen
/// oder Sonderzeichen enthält, damit Wortgrenzen sichtbar bleiben.
fn quote(arg: &str) -> String {
    let plain = !arg.is_empty()
        && arg
            .chars()
            .all(|c| c.is_alphanumeric() || "-_./=:,@+%".contains(c));
    if plain {
        arg.into()
    } else {
        format!("'{}'", arg.replace('\'', r"'\''"))
    }
}

impl Check {
    /// Lesbare Form für Nachweise; die Ausführung nutzt immer `argv` ohne Shell.
    pub fn command_line(&self) -> String {
        self.argv
            .iter()
            .map(|a| quote(a))
            .collect::<Vec<_>>()
            .join(" ")
    }
}

impl MemoryStore {
    /// Setzt den aktiven Prüfbefehl eines Eintrags; frühere bleiben als Historie erhalten.
    pub fn set_check(
        &self,
        memory_id: i64,
        argv: &[String],
        workdir: &str,
        set_by: &str,
    ) -> Result<i64> {
        nonblank(workdir)?;
        nonblank(set_by)?;
        let program = argv.first().ok_or_else(|| invalid("Prüfbefehl fehlt"))?;
        nonblank(program)?;
        let argv_chars: usize = argv.iter().map(|a| a.chars().count()).sum();
        if argv_chars > MAX_ARGV_CHARS
            || workdir.chars().count() > MAX_WORKDIR_CHARS
            || set_by.chars().count() > MAX_ACTOR_CHARS
        {
            return Err(invalid("Prüfbefehl überschreitet die Größenlimits"));
        }
        let record = self
            .get(memory_id)?
            .ok_or_else(|| invalid("Eintrag nicht gefunden"))?;
        if record.status == "invalidated" {
            return Err(invalid(
                "Zurückgezogene Einträge erhalten keinen Prüfbefehl",
            ));
        }
        let json = serde_json::to_string(argv).map_err(|_| invalid("Prüfbefehl ungültig"))?;
        self.conn.execute(
            "INSERT INTO memory_checks(memory_id, argv, workdir, set_by) VALUES (?1, ?2, ?3, ?4)",
            params![memory_id, json, workdir, set_by],
        )?;
        Ok(self.conn.last_insert_rowid())
    }

    pub fn active_check(&self, memory_id: i64) -> Result<Option<Check>> {
        self.conn
            .query_row(
                &format!(
                    "SELECT {CHECK_FIELDS} FROM memory_checks c
                    WHERE c.memory_id=?1 ORDER BY c.id DESC LIMIT 1"
                ),
                [memory_id],
                check_row,
            )
            .optional()
    }

    /// Letzte Läufe aller Prüfbefehle eines Eintrags, neueste zuerst.
    pub fn check_runs(&self, memory_id: i64, limit: usize) -> Result<Vec<CheckRun>> {
        if !(1..=100).contains(&limit) {
            return Err(invalid("Limit muss 1 bis 100 sein"));
        }
        let mut stmt = self.conn.prepare(
            "SELECT r.id, r.check_id, r.outcome, r.exit_code, r.duration_ms, r.output, r.created_at
            FROM check_runs r JOIN memory_checks c ON c.id=r.check_id
            WHERE c.memory_id=?1 ORDER BY r.id DESC LIMIT ?2",
        )?;
        stmt.query_map(params![memory_id, limit as i64], |row| {
            Ok(CheckRun {
                id: row.get(0)?,
                check_id: row.get(1)?,
                outcome: row.get(2)?,
                exit_code: row.get(3)?,
                duration_ms: row.get(4)?,
                output: row.get(5)?,
                created_at: row.get(6)?,
            })
        })?
        .collect()
    }

    /// Aktive Prüfbefehle nicht zurückgezogener Einträge im Bereich plus `global`.
    pub fn checks_in_scope(&self, scope: &str) -> Result<Vec<Check>> {
        nonblank(scope)?;
        let mut stmt = self.conn.prepare(&format!(
            "SELECT {CHECK_FIELDS} FROM memory_checks c JOIN memories m ON m.id=c.memory_id
            WHERE m.scope IN ('global', ?1)
            AND NOT EXISTS(SELECT 1 FROM invalidations i WHERE i.memory_id=m.id)
            AND c.id=(SELECT max(id) FROM memory_checks WHERE memory_id=m.id)
            ORDER BY m.id LIMIT ?2"
        ))?;
        stmt.query_map(params![scope, MAX_SCOPE_CHECKS], check_row)?
            .collect()
    }

    /// Speichert einen Lauf und leitet daraus den Status ab: Bestanden validiert einen
    /// ungeprüften Eintrag. Ein Fehlschlag zieht einen validierten Eintrag nur mit
    /// `invalidate_on_failure` zurück, weil ein Rückzug endgültig ist.
    pub fn apply_check(
        &self,
        check: &Check,
        result: &CheckResult,
        invalidate_on_failure: bool,
    ) -> Result<Applied> {
        let tx = self.conn.unchecked_transaction()?;
        let active = self.active_check(check.memory_id)?.map(|c| c.id);
        if active != Some(check.id) {
            return Err(invalid("Prüfbefehl wurde inzwischen ersetzt"));
        }
        let status_before = self
            .get(check.memory_id)?
            .ok_or_else(|| invalid("Eintrag nicht gefunden"))?
            .status;
        let duration_ms = i64::try_from(result.duration_ms).unwrap_or(i64::MAX);
        self.conn.execute(
            "INSERT INTO check_runs(check_id, outcome, exit_code, duration_ms, output)
            VALUES (?1, ?2, ?3, ?4, ?5)",
            params![
                check.id,
                result.outcome.as_str(),
                result.exit_code,
                duration_ms,
                tail(&result.output, MAX_OUTPUT_CHARS)
            ],
        )?;
        let run_id = self.conn.last_insert_rowid();
        let exit = result
            .exit_code
            .map_or_else(|| "–".to_string(), |c| c.to_string());
        match (result.outcome, status_before.as_str()) {
            (Outcome::Passed, "pending") => {
                let evidence = format!(
                    "Prüfbefehl #{} bestanden (Lauf #{run_id}): `{}` in {}, Exit {exit}, {duration_ms} ms",
                    check.id,
                    check.command_line(),
                    check.workdir
                );
                self.validate(check.memory_id, CHECK_ACTOR, &evidence)?;
            }
            (Outcome::Failed, "validated") if invalidate_on_failure => {
                let reason = format!(
                    "Prüfbefehl #{} fehlgeschlagen (Lauf #{run_id}): `{}`, Exit {exit}",
                    check.id,
                    check.command_line()
                );
                self.invalidate(check.memory_id, CHECK_ACTOR, &reason)?;
            }
            _ => {}
        }
        let status_after = self
            .get(check.memory_id)?
            .ok_or_else(|| invalid("Eintrag nicht gefunden"))?
            .status;
        tx.commit()?;
        Ok(Applied {
            memory_id: check.memory_id,
            check_id: check.id,
            run_id,
            outcome: result.outcome,
            status_before,
            status_after,
        })
    }
}
