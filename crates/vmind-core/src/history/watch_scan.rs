//! Begrenzter Scan der datierten Codex-Ordner `JJJJ/MM/TT` unter der konfigurierten Wurzel.
//! Symbolischen Links wird nie gefolgt: weder bei Jahres-, Monats- oder Tagesordnern noch bei
//! Dateien. Pfade entstehen nur durch Anhängen geprüfter Namen an die Wurzel.
use std::{
    fs, io,
    path::{Path, PathBuf},
    time::{SystemTime, UNIX_EPOCH},
};

const PREFIX: &str = "rollout-";
const SUFFIX: &str = ".jsonl";
const SECONDS_PER_DAY: u64 = 86_400;
/// Codex benennt Ordner nach lokalem Datum, V-Mind rechnet in UTC: einen Tag nach vorn zulassen.
const DAYS_AHEAD: i64 = 1;

/// Kalenderdatum (proleptisch gregorianisch) ohne zusätzliche Abhängigkeit.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct CivilDate {
    year: i64,
    month: u32,
    day: u32,
}

/// Tage seit 1970-01-01 (Verfahren nach Howard Hinnant).
fn days_from_civil(year: i64, month: u32, day: u32) -> i64 {
    let y = if month <= 2 { year - 1 } else { year };
    let era = y.div_euclid(400);
    let yoe = y - era * 400;
    let m = i64::from(month);
    let doy = (153 * (if m > 2 { m - 3 } else { m + 9 }) + 2) / 5 + i64::from(day) - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146_097 + doe - 719_468
}

fn civil_from_days(days: i64) -> CivilDate {
    let z = days + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let month = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    let year = yoe + era * 400 + i64::from(month <= 2);
    CivilDate { year, month, day }
}

impl CivilDate {
    /// `None` für ein ungültiges Datum wie den 30. Februar.
    pub fn new(year: i64, month: u32, day: u32) -> Option<Self> {
        if !(1..=12).contains(&month) || !(1..=31).contains(&day) || !(0..=9999).contains(&year) {
            return None;
        }
        let date = Self { year, month, day };
        (civil_from_days(days_from_civil(year, month, day)) == date).then_some(date)
    }

    pub fn today_utc() -> Self {
        let seconds = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_or(0, |d| d.as_secs());
        civil_from_days((seconds / SECONDS_PER_DAY) as i64)
    }

    pub fn add_days(self, days: i64) -> Self {
        civil_from_days(days_from_civil(self.year, self.month, self.day) + days)
    }

    /// Relativer Ordner `JJJJ/MM/TT`, wie Codex ihn anlegt.
    pub fn relative_dir(self) -> PathBuf {
        PathBuf::from(format!("{:04}", self.year))
            .join(format!("{:02}", self.month))
            .join(format!("{:02}", self.day))
    }
}

pub(super) struct Scan {
    pub(super) files: Vec<PathBuf>,
    /// Einträge in Tagesordnern, die keine reguläre `rollout-*.jsonl` sind.
    pub(super) ignored: u64,
    pub(super) root_missing: bool,
    /// Nicht lesbare Ordner; der Scan geht mit den übrigen weiter.
    pub(super) problems: Vec<(PathBuf, String)>,
}

/// Echter Ordner (kein Link) oder `Ok(false)`, wenn er fehlt oder etwas anderes ist.
fn real_dir(path: &Path) -> io::Result<bool> {
    match fs::symlink_metadata(path) {
        Ok(meta) => Ok(meta.is_dir()),
        Err(e) if e.kind() == io::ErrorKind::NotFound => Ok(false),
        Err(e) => Err(e),
    }
}

/// Tagesordner nur, wenn Jahr, Monat und Tag echte Ordner sind.
fn day_dir(root: &Path, date: CivilDate) -> io::Result<Option<PathBuf>> {
    let mut dir = root.to_path_buf();
    for part in date.relative_dir().components() {
        dir.push(part);
        if !real_dir(&dir)? {
            return Ok(None);
        }
    }
    Ok(Some(dir))
}

fn wanted(entry: &fs::DirEntry) -> io::Result<Option<String>> {
    // `DirEntry::file_type` folgt keinem Link; ein Link ist hier nie `is_file`.
    if !entry.file_type()?.is_file() {
        return Ok(None);
    }
    Ok(entry
        .file_name()
        .to_str()
        .filter(|n| n.starts_with(PREFIX) && n.ends_with(SUFFIX) && n.len() > PREFIX.len())
        .map(str::to_owned))
}

fn scan_day(dir: &Path, scan: &mut Scan) -> io::Result<()> {
    for entry in fs::read_dir(dir)? {
        match wanted(&entry?)? {
            Some(name) => scan.files.push(dir.join(name)),
            None => scan.ignored += 1,
        }
    }
    Ok(())
}

/// Ordner von `today - days` bis `today + 1` (UTC), älteste zuerst; Dateien je Tag sortiert.
pub(super) fn scan(root: &Path, today: CivilDate, days: u32) -> Result<Scan, String> {
    let mut scan = Scan {
        files: Vec::new(),
        ignored: 0,
        root_missing: false,
        problems: Vec::new(),
    };
    match fs::symlink_metadata(root) {
        Err(e) if e.kind() == io::ErrorKind::NotFound => {
            scan.root_missing = true;
            return Ok(scan);
        }
        Err(e) => return Err(format!("Sitzungswurzel nicht lesbar: {}", e.kind())),
        Ok(meta) if meta.file_type().is_symlink() => {
            return Err("Sitzungswurzel ist ein symbolischer Link; nicht gefolgt".into());
        }
        Ok(meta) if !meta.is_dir() => return Err("Sitzungswurzel ist kein Ordner".into()),
        Ok(_) => {}
    }
    for offset in -i64::from(days)..=DAYS_AHEAD {
        let date = today.add_days(offset);
        let start = scan.files.len();
        let result = day_dir(root, date).and_then(|dir| match dir {
            Some(dir) => scan_day(&dir, &mut scan),
            None => Ok(()),
        });
        if let Err(e) = result {
            scan.files.truncate(start);
            let message = format!("Ordner nicht lesbar: {}", e.kind());
            scan.problems
                .push((root.join(date.relative_dir()), message));
        }
        scan.files[start..].sort();
    }
    Ok(scan)
}
