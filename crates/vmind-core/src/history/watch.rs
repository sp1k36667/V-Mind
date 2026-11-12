//! Konfigurationsgesteuerter Einmallauf über die Codex-Sitzungen (`history-watch`). Je Datei
//! wird der Bereich aus `cwd` der ersten Zeile (`session_meta`) bestimmt; dann übernimmt der
//! inkrementelle Codex-Import. Nicht zugeordnete Dateien werden nur gezählt; von ihnen wird
//! nur die erste Zeile gelesen. Ein Fehler einer Quelle hält die übrigen nicht an.
use super::{
    watch_config::{WatchConfig, normalized},
    watch_scan::{CivilDate, scan},
};
use crate::MemoryStore;
use serde::Serialize;
use serde_json::Value;
use std::{
    fs::{File, TryLockError},
    io::{self, BufRead, BufReader, Read},
    path::{Path, PathBuf},
};

/// `session_meta` enthält Basisanweisungen und kann groß sein; darüber gilt die Datei als defekt.
const MAX_META_BYTES: u64 = 16 * 1024 * 1024;
const MAX_LISTED_ERRORS: usize = 50;

#[derive(Debug, Serialize)]
pub struct WatchProblem {
    pub source: String,
    /// Nie mit Zeileninhalt.
    pub error: String,
}

/// Zusammenfassung eines Laufs. `sources` = `imported + skipped + unassigned + failed` ohne
/// Ordnerfehler, die zusätzlich in `failed` zählen.
#[derive(Debug, Default, Serialize)]
pub struct WatchReport {
    pub root: String,
    pub days: u32,
    /// Die Wurzel fehlt; nichts gelesen.
    pub root_missing: bool,
    /// Gefundene reguläre `rollout-*.jsonl` im Zeitfenster.
    pub sources: u64,
    /// Quellen mit neuen Nachrichten.
    pub imported: u64,
    /// Neu gespeicherte Nachrichten.
    pub added: u64,
    /// Ohne neue Nachrichten oder mit noch unvollständiger erster Zeile.
    pub skipped: u64,
    /// Kein Bereich passt zu `cwd`; die Datei wurde nicht importiert.
    pub unassigned: u64,
    pub failed: u64,
    /// Andere Einträge in Tagesordnern: Links, `.zst`, fremde Namen, Unterordner.
    pub ignored: u64,
    /// Höchstens 50, älteste Tage zuerst.
    pub errors: Vec<WatchProblem>,
}

impl WatchReport {
    fn fail(&mut self, source: &Path, error: String) {
        self.failed += 1;
        if self.errors.len() < MAX_LISTED_ERRORS {
            self.errors.push(WatchProblem {
                source: source.to_string_lossy().into_owned(),
                error,
            });
        }
    }
}

enum Origin {
    Cwd(PathBuf),
    /// Erste Zeile noch nicht vollständig geschrieben.
    Waiting,
}

/// Liest nur die erste Zeile. Meldungen enthalten nie Dateiinhalt.
fn session_cwd(path: &Path) -> Result<Origin, String> {
    let file = File::open(path).map_err(|e| format!("Datei nicht lesbar: {}", e.kind()))?;
    let mut line = Vec::new();
    BufReader::new(file)
        .take(MAX_META_BYTES + 1)
        .read_until(b'\n', &mut line)
        .map_err(|e| format!("Datei nicht lesbar: {}", e.kind()))?;
    if line.len() as u64 > MAX_META_BYTES {
        return Err("Erste Zeile überschreitet die Größengrenze".into());
    }
    if line.last() != Some(&b'\n') {
        return Ok(Origin::Waiting);
    }
    let row: Value = serde_json::from_slice(&line)
        .map_err(|_| "Bereich nicht bestimmbar: erste Zeile ist kein JSON".to_owned())?;
    if row["type"].as_str() != Some("session_meta") {
        return Err("Bereich nicht bestimmbar: erste Zeile ist keine session_meta".into());
    }
    row["payload"]["cwd"]
        .as_str()
        .filter(|c| !c.is_empty() && !c.chars().any(char::is_control))
        .map(|c| Origin::Cwd(PathBuf::from(c)))
        .ok_or_else(|| "Bereich nicht bestimmbar: session_meta ohne gültiges cwd".into())
}

/// Exklusive Betriebssystem-Sperre (flock) auf `path`. `None`, wenn ein anderer Lauf sie hält.
/// Die Sperre hängt am Dateihandle und endet spätestens mit dem Prozess, auch nach Absturz;
/// es bleibt keine Sperrdatei zurück, die aufgeräumt werden müsste.
pub fn try_watch_lock(path: &Path) -> io::Result<Option<File>> {
    let file = File::open(path)?;
    match file.try_lock() {
        Ok(()) => Ok(Some(file)),
        Err(TryLockError::WouldBlock) => Ok(None),
        Err(TryLockError::Error(e)) => Err(e),
    }
}

impl MemoryStore {
    /// Ein Lauf über das Zeitfenster der Konfiguration. `Err` nur, wenn die Wurzel selbst
    /// unbrauchbar ist; alle Fehler einzelner Quellen stehen im Bericht, Importfehler
    /// zugeordneter Quellen zusätzlich im Importstand (`history-status`).
    pub fn watch_codex_history(
        &self,
        config: &WatchConfig,
        today: CivilDate,
    ) -> Result<WatchReport, String> {
        let found = scan(config.codex_sessions(), today, config.days())?;
        let mut report = WatchReport {
            root: config.codex_sessions().to_string_lossy().into_owned(),
            days: config.days(),
            root_missing: found.root_missing,
            ignored: found.ignored,
            ..WatchReport::default()
        };
        for (dir, error) in found.problems {
            report.fail(&dir, error);
        }
        for path in found.files {
            report.sources += 1;
            self.watch_one(config, &path, &mut report);
        }
        Ok(report)
    }

    fn watch_one(&self, config: &WatchConfig, path: &Path, report: &mut WatchReport) {
        let cwd = match session_cwd(path) {
            Ok(Origin::Cwd(cwd)) => cwd,
            Ok(Origin::Waiting) => {
                report.skipped += 1;
                return;
            }
            Err(error) => return report.fail(path, error),
        };
        let Some(scope) = normalized(&cwd).and_then(|c| config.scope_for(&c)) else {
            report.unassigned += 1;
            return;
        };
        match self.import_codex_history_file(scope, path) {
            Ok(done) => match done.error {
                Some(error) => report.fail(path, error),
                None if done.added > 0 => {
                    report.imported += 1;
                    report.added += done.added as u64;
                }
                None => report.skipped += 1,
            },
            Err(error) => report.fail(path, format!("Datenbankfehler: {error}")),
        }
    }
}
