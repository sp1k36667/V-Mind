//! Reparaturwissen: Ein Prüfbefehl schlug fehl und bestand im unmittelbar folgenden Lauf.
//! Daraus darf der Aufrufer einen ungeprüften Eintrag vorschlagen. Problem und Lösung
//! schreibt er selbst; Ausgabe und Befehl der Läufe werden nie übernommen.
use crate::{MemoryStore, invalid, nonblank, retry_busy};
use rusqlite::{OptionalExtension, Result, Transaction, TransactionBehavior, params};
use serde::Serialize;

const MAX_REPAIRS: i64 = 100;
/// So viele Lauf-IDs offener Reparaturen zeigt der Fortsetzungsstand.
const OPEN_REPAIR_RUNS: i64 = 3;

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
    /// Bereich des geprüften Eintrags (der Aufrufbereich oder `global`).
    pub scope: String,
    /// Von V-Mind erzeugte Quelle eines Vorschlags; dient der Deduplizierung, ist aber kein
    /// manipulationssicherer Nachweis, weil Quellen sonst frei wählbar sind.
    pub source: String,
}

/// Reparaturen ohne Vorschlag im Aufrufbereich: echte Gesamtzahl und die neuesten Läufe.
#[derive(Debug, Default, Serialize)]
pub struct OpenRepairs {
    pub total: i64,
    /// Höchstens drei `failed_run`-IDs, neueste zuerst; für `propose-repair`.
    pub newest_failed_runs: Vec<i64>,
}

/// Einzige Definition der kanonischen Quelle; Liste, Vorschlag und Zähler nutzen sie.
const SOURCE_SQL: &str = "'Reparatur: Prüfbefehl #' || c.id || ' an Eintrag #' || c.memory_id
    || ', Lauf #' || f.id || ' fehlgeschlagen → Lauf #' || p.id || ' bestanden'";

/// Übergänge failed → passed desselben aktiven Prüfbefehls (ohne Lauf dazwischen) an nicht
/// zurückgezogenen Einträgen im Bereich `?1` plus `global`.
const REPAIRS_FROM: &str = "
    FROM check_runs f
    JOIN memory_checks c ON c.id=f.check_id
    JOIN memories m ON m.id=c.memory_id
    JOIN check_runs p ON p.id=(SELECT min(id) FROM check_runs WHERE check_id=f.check_id AND id>f.id)
    WHERE f.outcome='failed' AND p.outcome='passed'
    AND m.scope IN ('global', ?1)
    AND NOT EXISTS(SELECT 1 FROM invalidations i WHERE i.memory_id=m.id)
    AND c.id=(SELECT max(id) FROM memory_checks WHERE memory_id=m.id)";

/// Liste; `?3` grenzt optional auf einen Lauf ein, `?2` begrenzt.
fn repairs_sql() -> String {
    format!(
        "SELECT c.memory_id, c.id, f.id, p.id, f.exit_code, p.exit_code, f.created_at,
            p.created_at, m.scope, {SOURCE_SQL} {REPAIRS_FROM}
        AND (?3 IS NULL OR f.id=?3) ORDER BY f.id DESC LIMIT ?2"
    )
}

/// Bedingung: im Aufrufbereich `?1` gibt es noch keinen Vorschlag zu diesem Laufpaar.
fn unproposed() -> String {
    format!("AND NOT EXISTS(SELECT 1 FROM memories x WHERE x.scope=?1 AND x.source={SOURCE_SQL})")
}

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
        source: row.get(9)?,
    })
}

impl MemoryStore {
    /// Neueste Reparaturen zuerst, höchstens 100.
    pub fn repairs(&self, scope: &str) -> Result<Vec<Repair>> {
        nonblank(scope)?;
        let mut stmt = self.conn.prepare(&repairs_sql())?;
        stmt.query_map(params![scope, MAX_REPAIRS, None::<i64>], repair_row)?
            .collect()
    }

    /// Nur lesend: sichtbare Reparaturen, zu denen der Aufrufbereich noch keinen Vorschlag hat.
    pub fn open_repairs(&self, scope: &str) -> Result<OpenRepairs> {
        nonblank(scope)?;
        let open = unproposed();
        let total = self.conn.query_row(
            &format!("SELECT count(*) {REPAIRS_FROM} {open}"),
            [scope],
            |r| r.get(0),
        )?;
        let mut stmt = self.conn.prepare(&format!(
            "SELECT f.id {REPAIRS_FROM} {open} ORDER BY f.id DESC LIMIT ?2"
        ))?;
        let newest_failed_runs = stmt
            .query_map(params![scope, OPEN_REPAIR_RUNS], |r| r.get(0))?
            .collect::<Result<_>>()?;
        Ok(OpenRepairs {
            total,
            newest_failed_runs,
        })
    }

    /// Legt zu einer sichtbaren Reparatur genau einen ungeprüften Eintrag im Aufrufbereich
    /// an; ein Projekt macht seinen Text so nicht über einen globalen Prüfbefehl global.
    /// Je Zielbereich gibt es einen Vorschlag pro Laufpaar. Prüfung des Laufpaars, Suche
    /// nach einem früheren Vorschlag und Anlage laufen in einer Schreibtransaktion, damit
    /// gleichzeitige Aufrufe keinen zweiten Eintrag anlegen.
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
                .query_row(&repairs_sql(), params![scope, 1, failed_run], repair_row)
                .optional()?
                .ok_or_else(|| {
                    invalid("Kein sichtbarer Übergang fehlgeschlagen → bestanden für diesen Lauf")
                })?;
            let source = repair.source;
            let known: bool = self.conn.query_row(
                "SELECT EXISTS(SELECT 1 FROM memories WHERE source=?1 AND scope=?2)",
                params![source, scope],
                |r| r.get(0),
            )?;
            if known {
                return Err(invalid(
                    "Für diese Reparatur gibt es in diesem Bereich bereits einen Vorschlag",
                ));
            }
            let id = self.remember_scoped(scope, "error_solution", problem, solution, &source)?;
            tx.commit()?;
            Ok(id)
        })
    }
}
