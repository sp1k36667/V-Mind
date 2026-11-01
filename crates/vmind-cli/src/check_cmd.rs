//! CLI-Befehle für Prüfbefehle. Nur die Kommandozeile darf Prüfbefehle setzen und
//! ausführen; JSONL und MCP lesen sie lediglich.
use crate::{Result, emit, runner};
use serde_json::json;
use std::{env, io, path::Path, time::Duration};
use vmind_core::{Applied, Check, CheckResult, MemoryStore, Outcome};

const DEFAULT_TIMEOUT_SECS: u64 = 300;
const MAX_TIMEOUT_SECS: u64 = 3600;
const SHOWN_OUTPUT_CHARS: usize = 1500;

fn timeout() -> Result<Duration> {
    let Ok(raw) = env::var("VMIND_CHECK_TIMEOUT") else {
        return Ok(Duration::from_secs(DEFAULT_TIMEOUT_SECS));
    };
    match raw.parse::<u64>() {
        Ok(secs) if (1..=MAX_TIMEOUT_SECS).contains(&secs) => Ok(Duration::from_secs(secs)),
        _ => Err(io::Error::other("VMIND_CHECK_TIMEOUT muss 1 bis 3600 Sekunden sein").into()),
    }
}

fn tail(text: &str, max: usize) -> &str {
    let count = text.chars().count();
    if count <= max {
        return text;
    }
    let start = text.char_indices().nth(count - max).map_or(0, |(i, _)| i);
    &text[start..]
}

fn line(applied: &Applied, check: &Check) -> String {
    let change = if applied.status_before == applied.status_after {
        applied.status_after.clone()
    } else {
        format!("{} → {}", applied.status_before, applied.status_after)
    };
    format!(
        "#{} {:?} ({change}): `{}`",
        applied.memory_id,
        applied.outcome,
        check.command_line()
    )
}

fn execute(
    store: &MemoryStore,
    check: &Check,
    invalidate: bool,
    json_mode: bool,
) -> Result<(Applied, CheckResult)> {
    if !json_mode {
        eprintln!(
            "Prüfe #{}: `{}` in {}",
            check.memory_id,
            check.command_line(),
            check.workdir
        );
    }
    let result = runner::run(check, timeout()?);
    let applied = store.apply_check(check, &result, invalidate)?;
    Ok((applied, result))
}

pub fn set(
    db: &str,
    id: &str,
    actor: &str,
    dir: &str,
    argv: &[String],
    json_mode: bool,
) -> Result<()> {
    let workdir = Path::new(dir).canonicalize()?;
    if !workdir.is_dir() {
        return Err(io::Error::other("Arbeitsordner ist kein Verzeichnis").into());
    }
    let workdir = workdir
        .to_str()
        .ok_or_else(|| io::Error::other("Arbeitsordner ist kein gültiges UTF-8"))?;
    let store = MemoryStore::open_existing(db)?;
    let memory_id: i64 = id.parse()?;
    let check_id = store.set_check(memory_id, argv, workdir, actor)?;
    emit(
        json!({"memory_id":memory_id,"check_id":check_id,"argv":argv,"workdir":workdir}),
        format!(
            "Prüfbefehl #{check_id} für Eintrag {memory_id} gesetzt: `{}` in {workdir}",
            argv.join(" ")
        ),
        json_mode,
    )
}

pub fn check_one(db: &str, id: &str, invalidate: bool, json_mode: bool) -> Result<()> {
    let store = MemoryStore::open_existing(db)?;
    let memory_id: i64 = id.parse()?;
    let record = store
        .get(memory_id)?
        .ok_or_else(|| io::Error::other("Eintrag nicht gefunden"))?;
    if record.status == "invalidated" {
        return Err(io::Error::other("Eintrag ist zurückgezogen").into());
    }
    let check = store
        .active_check(memory_id)?
        .ok_or_else(|| io::Error::other("Eintrag hat keinen Prüfbefehl"))?;
    let (applied, result) = execute(&store, &check, invalidate, json_mode)?;
    let mut human = line(&applied, &check);
    if applied.outcome != Outcome::Passed {
        human = format!("{human}\n{}", tail(&result.output, SHOWN_OUTPUT_CHARS));
    }
    emit(
        json!({"applied":applied,"exit_code":result.exit_code,"duration_ms":result.duration_ms}),
        human,
        json_mode,
    )?;
    if applied.outcome == Outcome::Passed {
        Ok(())
    } else {
        Err(io::Error::other("Prüfung nicht bestanden").into())
    }
}

pub fn revalidate(db: &str, scope: &str, invalidate: bool, json_mode: bool) -> Result<()> {
    let store = MemoryStore::open_existing(db)?;
    let checks = store.checks_in_scope(scope)?;
    let mut applied = Vec::with_capacity(checks.len());
    let mut lines = Vec::with_capacity(checks.len());
    for check in &checks {
        let (result, _) = execute(&store, check, invalidate, json_mode)?;
        lines.push(line(&result, check));
        applied.push(result);
    }
    let failed = applied
        .iter()
        .filter(|a| a.outcome != Outcome::Passed)
        .count();
    let summary = format!(
        "{} Prüfungen im Bereich {scope} + global, {failed} nicht bestanden.",
        checks.len()
    );
    lines.push(summary);
    emit(
        json!({"scope":scope,"results":applied,"failed":failed}),
        lines.join("\n"),
        json_mode,
    )?;
    if failed == 0 {
        Ok(())
    } else {
        Err(io::Error::other(format!("{failed} Prüfungen nicht bestanden")).into())
    }
}

/// The check result is evidence at run_at, never an assertion about today's code.
pub(crate) fn evidence_note(check: &vmind_core::CheckEvidence) -> String {
    use vmind_core::CheckState;
    let at = check.run_at.as_deref().unwrap_or("unbekannt");
    match check.state {
        CheckState::None => "kein Prüfbefehl ausgeführt".into(),
        CheckState::NotRun => "Hinweis: aktiver Prüfbefehl noch nicht ausgeführt; frühere Läufe anderer Definitionen sind kein Nachweis".into(),
        CheckState::Passed => format!("letzter Lauf des aktiven Prüfbefehls bestanden am {at}; heutiger Stand nicht erneut geprüft"),
        CheckState::Failed => format!("WARNUNG: aktiver Prüfbefehl fehlgeschlagen am {at}; Validierungsstatus unverändert, Neuprüfung nötig"),
        CheckState::Error => {
            let verdict = check.last_verdict.as_ref().map_or(String::new(), |v|
                format!("; letzter Pass/Fail-Befund dieser Definition: {} am {}", v.outcome, v.run_at));
            format!("Hinweis: Ausführungsfehler am {at}, keine neue Gültigkeitsaussage{verdict}")
        }
    }
}
