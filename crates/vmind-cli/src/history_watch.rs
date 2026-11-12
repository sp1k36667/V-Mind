//! `history-watch`: konfigurationsgesteuerter Einmallauf über die Codex-Sitzungen.
//! `history-watch-units`: erzeugt eine systemd-User-Service- und Timer-Unit als Text, installiert
//! und aktiviert aber nichts. Ohne Konfiguration wird keine Quelle gelesen.
use crate::{Result, emit};
use serde_json::{Value, json};
use std::{
    env, fs,
    io::{self, Read, Write},
    path::{Path, PathBuf},
};
use vmind_core::{CivilDate, MemoryStore, WatchConfig, WatchReport, try_watch_lock};

const CONFIG_FILE: &str = "vmind/history.json";
const MAX_CONFIG_BYTES: u64 = 1024 * 1024;
const SERVICE: &str = "vmind-history-watch.service";
const TIMER: &str = "vmind-history-watch.timer";
const DEFAULT_INTERVAL: u32 = 15;
const MAX_INTERVAL: u32 = 1440;

fn usage(message: &str) -> Box<dyn std::error::Error> {
    io::Error::other(message.to_owned()).into()
}

fn absolute_env(name: &str) -> Option<PathBuf> {
    env::var_os(name)
        .map(PathBuf::from)
        .filter(|p| p.is_absolute())
}

/// `--config`, sonst `$XDG_CONFIG_HOME/vmind/history.json`, sonst `~/.config/…`.
fn config_path(explicit: Option<&str>) -> Option<PathBuf> {
    match explicit {
        Some(path) => Some(PathBuf::from(path)),
        None => absolute_env("XDG_CONFIG_HOME")
            .or_else(|| absolute_env("HOME").map(|h| h.join(".config")))
            .map(|base| base.join(CONFIG_FILE)),
    }
}

/// Liest Optionen `--NAME WERT` aus einer erlaubten Liste; jede höchstens einmal.
fn options<'a>(
    args: &'a [String],
    allowed: &[&str],
    call: &str,
) -> Result<Vec<(&'a str, &'a str)>> {
    let mut found: Vec<(&str, &str)> = Vec::new();
    let mut rest = args;
    while let [flag, value, tail @ ..] = rest {
        let name = flag.as_str();
        if !allowed.contains(&name) || found.iter().any(|(n, _)| *n == name) {
            break;
        }
        found.push((name, value.as_str()));
        rest = tail;
    }
    if !rest.is_empty() {
        return Err(usage(call));
    }
    Ok(found)
}

fn option<'a>(found: &[(&str, &'a str)], name: &str) -> Option<&'a str> {
    found.iter().find(|(n, _)| *n == name).map(|(_, v)| *v)
}

/// `Ok(None)`, wenn die Datei fehlt: Dann ist nichts eingerichtet.
fn read_config(path: &Path) -> Result<Option<String>> {
    let meta = match fs::metadata(path) {
        Ok(meta) => meta,
        Err(e) if e.kind() == io::ErrorKind::NotFound => return Ok(None),
        Err(e) => return Err(usage(&format!("Konfiguration nicht lesbar: {}", e.kind()))),
    };
    if !meta.is_file() || meta.len() > MAX_CONFIG_BYTES {
        return Err(usage("Konfiguration ist keine reguläre Datei bis 1 MiB"));
    }
    let mut text = String::new();
    fs::File::open(path)?
        .take(MAX_CONFIG_BYTES)
        .read_to_string(&mut text)?;
    Ok(Some(text))
}

fn report_text(report: &WatchReport) -> String {
    let mut lines = vec![format!(
        "Codex-Verlauf (Wurzel {}, Fenster {} Tage):",
        report.root, report.days
    )];
    if report.root_missing {
        lines.push("  Sitzungswurzel fehlt; nichts gelesen.".into());
    }
    lines.push(format!(
        "  Quellen: {}, importiert: {} ({} neue Nachrichten), übersprungen: {}, \
         nicht zugeordnet: {}, Fehler: {}, ignoriert: {}",
        report.sources,
        report.imported,
        report.added,
        report.skipped,
        report.unassigned,
        report.failed,
        report.ignored
    ));
    lines.extend(
        report
            .errors
            .iter()
            .map(|e| format!("  FEHLER: {}: {}", e.source, e.error)),
    );
    lines.join("\n")
}

fn status(name: &str, config: Option<&Path>) -> Value {
    json!({"status":name,"config":config.map(|p| p.to_string_lossy())})
}

pub fn run(args: &[String], json_mode: bool) -> Result<()> {
    let found = options(args, &["--config"], "Aufruf: history-watch [--config PFAD]")?;
    let Some(path) = config_path(option(&found, "--config")) else {
        let text = "Keine Konfiguration (HOME nicht gesetzt); keine Quelle gelesen.".into();
        return emit(status("not_configured", None), text, json_mode);
    };
    let Some(text) = read_config(&path)? else {
        let text = format!(
            "Keine Konfiguration unter {}; keine Quelle gelesen.",
            path.display()
        );
        return emit(status("not_configured", Some(&path)), text, json_mode);
    };
    let home = absolute_env("HOME");
    let config = WatchConfig::parse(&text, home.as_deref()).map_err(|e| usage(&e))?;
    // Die Sperre hält bis zum Ende dieser Funktion, nach Absturz gibt das System sie frei.
    let Some(_lock) = try_watch_lock(&path)? else {
        let text = "Ein anderer history-watch-Lauf hält die Sperre; übersprungen.".into();
        return emit(status("locked", Some(&path)), text, json_mode);
    };
    let store = MemoryStore::open_current(config.database())?;
    let report = store
        .watch_codex_history(&config, CivilDate::today_utc())
        .map_err(|e| usage(&e))?;
    let text = report_text(&report);
    let mut value = serde_json::to_value(&report)?;
    value["status"] = json!("completed");
    value["config"] = json!(path.to_string_lossy());
    emit(value, text, json_mode)
}

/// Ein Argument für `ExecStart`: in Anführungszeichen, `%` und `$` verdoppelt, damit systemd
/// keine Platzhalter oder Variablen einsetzt. Steuerzeichen und relative Pfade sind abgelehnt.
fn unit_arg(value: &str) -> Result<String> {
    if value.chars().any(char::is_control) {
        return Err(usage(
            "Pfad mit Steuerzeichen ist für eine Unit nicht zulässig",
        ));
    }
    let escaped = value
        .replace('\\', "\\\\")
        .replace('"', "\\\"")
        .replace('%', "%%")
        .replace('$', "$$");
    Ok(format!("\"{escaped}\""))
}

fn absolute_arg(path: &Path, what: &str) -> Result<String> {
    let text = path
        .to_str()
        .filter(|_| path.is_absolute())
        .ok_or_else(|| usage(&format!("{what} muss ein absoluter UTF-8-Pfad sein")))?;
    unit_arg(text)
}

fn service_unit(vmind: &str, config: &str) -> String {
    format!(
        "# Erzeugt von `vmind history-watch-units`; nicht installiert und nicht aktiviert.\n\
         [Unit]\n\
         Description=V-Mind: Codex-Verlauf importieren (history-watch)\n\
         \n\
         [Service]\n\
         Type=oneshot\n\
         ExecStart={vmind} \"history-watch\" \"--config\" {config}\n\
         Nice=10\n"
    )
}

fn timer_unit(minutes: u32) -> String {
    format!(
        "# Erzeugt von `vmind history-watch-units`; nicht installiert und nicht aktiviert.\n\
         [Unit]\n\
         Description=V-Mind: Codex-Verlauf alle {minutes} Minuten importieren\n\
         \n\
         [Timer]\n\
         OnBootSec=2min\n\
         OnUnitActiveSec={minutes}min\n\
         Unit={SERVICE}\n\
         \n\
         [Install]\n\
         WantedBy=timers.target\n"
    )
}

/// Schreibt beide Dateien neu in `dir`; vorhandene Dateien werden nie überschrieben.
fn write_units(dir: &Path, service: &str, timer: &str) -> Result<Vec<String>> {
    if !fs::metadata(dir).is_ok_and(|m| m.is_dir()) {
        return Err(usage("--output muss ein vorhandener Ordner sein"));
    }
    let targets = [(dir.join(SERVICE), service), (dir.join(TIMER), timer)];
    if let Some((path, _)) = targets
        .iter()
        .find(|(p, _)| fs::symlink_metadata(p).is_ok())
    {
        return Err(usage(&format!(
            "{} existiert bereits; nichts überschrieben",
            path.display()
        )));
    }
    let mut written = Vec::new();
    for (path, body) in &targets {
        let mut file = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)?;
        file.write_all(body.as_bytes())?;
        written.push(path.to_string_lossy().into_owned());
    }
    Ok(written)
}

pub fn units(args: &[String], json_mode: bool) -> Result<()> {
    let call = "Aufruf: history-watch-units [--config PFAD] [--interval MINUTEN] \
                [--output ORDNER] [--vmind PFAD]";
    let found = options(
        args,
        &["--config", "--interval", "--output", "--vmind"],
        call,
    )?;
    let minutes = match option(&found, "--interval") {
        None => DEFAULT_INTERVAL,
        Some(value) => value
            .parse()
            .ok()
            .filter(|m| (1..=MAX_INTERVAL).contains(m))
            .ok_or_else(|| usage(&format!("--interval muss 1 bis {MAX_INTERVAL} sein")))?,
    };
    let config = config_path(option(&found, "--config"))
        .ok_or_else(|| usage("Konfigurationspfad unbekannt: --config angeben oder HOME setzen"))?;
    let vmind = match option(&found, "--vmind") {
        Some(path) => PathBuf::from(path),
        None => env::current_exe()?,
    };
    let service = service_unit(
        &absolute_arg(&vmind, "--vmind")?,
        &absolute_arg(&config, "--config")?,
    );
    let timer = timer_unit(minutes);
    let written = match option(&found, "--output") {
        Some(dir) => write_units(Path::new(dir), &service, &timer)?,
        None => Vec::new(),
    };
    let text = if written.is_empty() {
        format!("# Datei: {SERVICE}\n{service}\n# Datei: {TIMER}\n{timer}")
    } else {
        format!(
            "Geschrieben: {}. Nicht installiert und nicht aktiviert.",
            written.join(", ")
        )
    };
    emit(
        json!({"service_name":SERVICE,"timer_name":TIMER,"service":service,"timer":timer,
            "written":written,"installed":false}),
        text,
        json_mode,
    )
}
