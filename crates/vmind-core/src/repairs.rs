//! Reparaturwissen: Ein Prüfbefehl schlug fehl und bestand im unmittelbar folgenden Lauf.
//! Daraus darf der Aufrufer einen ungeprüften Eintrag vorschlagen. Problem und Lösung
//! schreibt er selbst; Ausgabe und Befehl der Läufe werden nie übernommen.
use crate::{MemoryStore, invalid, nonblank, retry_busy};
use rusqlite::{OptionalExtension, Result, Transaction, TransactionBehavior, params};
use serde::Serialize;

const MAX_REPAIRS: i64 = 100;

#[derive(Debug, Serialize)]
pub struct Repair {
    pub memory_id: i64,
    pub check_id: i64,
    pub failed_run: i64,
    pub passed_run: i64,
    pub failed_exit: Option<i64>,
    pub passed_exit: Option<i64>,
    pub failed_at: String,
    pub passed_at: String,
    /// Bereich des geprüften Eintrags; dort landet auch ein Vorschlag.
    pub scope: String,
}

/// Übergänge failed → passed desselben aktiven Prüfbefehls (ohne Lauf dazwischen) an nicht
/// zurückgezogenen Einträgen im Bereich plus `global`. `?3` grenzt optional auf einen Lauf ein.
const REPAIRS_SQL: &str = "
    SELECT c.memory_id, c.id, f.id, p.id, f.exit_code, p.exit_code, f.created_at, p.created_at,
        m.scope
    FROM check_runs f
    JOIN memory_checks c ON c.id=f.check_id
    JOIN memories m ON m.id=c.memory_id
    JOIN check_runs p ON p.id=(SELECT min(id) FROM check_runs WHERE check_id=f.check_id AND id>f.id)
    WHERE f.outcome='failed' AND p.outcome='passed'
    AND m.scope IN ('global', ?1)
    AND NOT EXISTS(SELECT 1 FROM invalidations i WHERE i.memory_id=m.id)
    AND c.id=(SELECT max(id) FROM memory_checks WHERE memory_id=m.id)
    AND (?3 IS NULL OR f.id=?3)
    ORDER BY f.id DESC LIMIT ?2";

fn repair_row(row: &rusqlite::Row<'_>) -> Result<Repair> {
    Ok(Repair {
        memory_id: row.get(0)?,
        check_id: row.get(1)?,
        failed_run: row.get(2)?,
        passed_run: row.get(3)?,
        failed_exit: row.get(4)?,
        passed_exit: row.get(5)?,
        failed_at: row.get(6)?,
        passed_at: row.get(7)?,
        scope: row.get(8)?,
    })
}

impl Repair {
    /// Von V-Mind erzeugte Quelle; dient der Deduplizierung, ist aber kein
    /// manipulationssicherer Nachweis, weil Quellen sonst frei wählbar sind.
    pub fn source(&self) -> String {
        format!(
            "Reparatur: Prüfbefehl #{} an Eintrag #{}, Lauf #{} fehlgeschlagen → Lauf #{} bestanden",
            self.check_id, self.memory_id, self.failed_run, self.passed_run
        )
    }
}

impl MemoryStore {
    /// Neueste Reparaturen zuerst, höchstens 100.
    pub fn repairs(&self, scope: &str) -> Result<Vec<Repair>> {
        nonblank(scope)?;
        let mut stmt = self.conn.prepare(REPAIRS_SQL)?;
        stmt.query_map(params![scope, MAX_REPAIRS, None::<i64>], repair_row)?
            .collect()
    }

    /// Legt zu einer sichtbaren Reparatur genau einen ungeprüften Eintrag an. Prüfung des
    /// Laufpaars, Suche nach einem früheren Vorschlag und Anlage laufen in einer
    /// Schreibtransaktion, damit gleichzeitige Aufrufe keinen zweiten Eintrag anlegen.
    pub fn propose_repair(
        &self,
        scope: &str,
        failed_run: i64,
        problem: &str,
        solution: &str,
    ) -> Result<i64> {
        nonblank(scope)?;
        nonblank(problem)?;
        nonblank(solution)?;
        retry_busy(&self.conn, || {
            let tx = Transaction::new_unchecked(&self.conn, TransactionBehavior::Immediate)?;
            let repair = self
                .conn
                .query_row(REPAIRS_SQL, params![scope, 1, failed_run], repair_row)
                .optional()?
                .ok_or_else(|| {
                    invalid("Kein sichtbarer Übergang fehlgeschlagen → bestanden für diesen Lauf")
                })?;
            let source = repair.source();
            let known: bool = self.conn.query_row(
                "SELECT EXISTS(SELECT 1 FROM memories WHERE source=?1)",
                [&source],
                |r| r.get(0),
            )?;
            if known {
                return Err(invalid(
                    "Für diese Reparatur gibt es bereits einen Vorschlag",
                ));
            }
            let id =
                self.remember_scoped(&repair.scope, "error_solution", problem, solution, &source)?;
            tx.commit()?;
            Ok(id)
        })
    }
}
