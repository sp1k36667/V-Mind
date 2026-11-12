//! Konfigurationsgesteuerter Codex-Import (`history-watch`): nur synthetische Sitzungsbäume in
//! einem Temp-Ordner mit überschriebener Wurzel; echte Dateien unter `~/.codex` nie.
use serde_json::{Value, json};
use std::{
    fs::{self, OpenOptions},
    io::Write,
    path::{Path, PathBuf},
};
use vmind_core::{CivilDate, MemoryStore, WatchConfig, WatchReport, try_watch_lock};

const STAMP: &str = "2026-03-01T10:00:00.000Z";

struct Temp(PathBuf);
impl Temp {
    fn new() -> Self {
        let p = std::env::temp_dir().join(format!(
            "vmind-watch-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir(&p).unwrap();
        Self(p)
    }
    fn db(&self) -> PathBuf {
        self.0.join("v.db")
    }
    fn root(&self) -> PathBuf {
        self.0.join("sessions")
    }
    fn store(&self) -> MemoryStore {
        MemoryStore::open_file(self.db()).unwrap()
    }
    /// Tagesordner unter der Wurzel, bei Bedarf angelegt.
    fn day(&self, date: CivilDate) -> PathBuf {
        let dir = self.root().join(date.relative_dir());
        fs::create_dir_all(&dir).unwrap();
        dir
    }
    fn config(&self, rules: Value, days: u32) -> WatchConfig {
        let text = json!({
            "database": self.db(),
            "codex_sessions": self.root(),
            "days": days,
            "scopes": rules,
        })
        .to_string();
        WatchConfig::parse(&text, None).unwrap()
    }
}
impl Drop for Temp {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn today() -> CivilDate {
    CivilDate::new(2026, 3, 1).unwrap()
}

fn meta(session: &str, cwd: &str) -> Value {
    json!({"timestamp":STAMP,"type":"session_meta","payload":{"id":session,"cwd":cwd}})
}
fn user(id: &str, text: &str) -> Value {
    json!({"timestamp":STAMP,"type":"event_msg","payload":{"type":"item_completed","turn_id":"t1",
        "item":{"type":"UserMessage","id":id,"client_id":"c","content":[{"type":"text","text":text}]}}})
}
fn lines(rows: &[Value]) -> String {
    rows.iter().map(|r| format!("{r}\n")).collect()
}
fn rollout(dir: &Path, name: &str, session: &str, cwd: &str, texts: &[&str]) -> PathBuf {
    let mut rows = vec![meta(session, cwd)];
    for (i, text) in texts.iter().enumerate() {
        rows.push(user(&format!("{session}-{i}"), text));
    }
    let path = dir.join(name);
    fs::write(&path, lines(&rows)).unwrap();
    path
}
fn rules() -> Value {
    json!([{"cwd":"/a/project","scope":"p1"},{"cwd":"/a/project/sub","scope":"p2"}])
}
fn run(t: &Temp, config: &WatchConfig) -> WatchReport {
    t.store().watch_codex_history(config, today()).unwrap()
}
fn found(t: &Temp, scope: &str, word: &str) -> usize {
    t.store().history_search(scope, word, 20).unwrap().len()
}

#[test]
fn ambiguous_config_with_equal_prefixes_is_rejected() {
    let text = json!({"database":"/d/v.db","codex_sessions":"/c",
        "scopes":[{"cwd":"/a/project","scope":"p1"},{"cwd":"/a/project/","scope":"p2"}]});
    let error = WatchConfig::parse(&text.to_string(), None).unwrap_err();
    assert!(error.contains("Mehrdeutig"), "{error}");
    // Gleicher Pfad mit gleichem Bereich ist nur doppelt, nicht mehrdeutig.
    let same = json!({"database":"/d/v.db","codex_sessions":"/c",
        "scopes":[{"cwd":"/a/project","scope":"p1"},{"cwd":"/a/./project","scope":"p1"}]});
    assert!(WatchConfig::parse(&same.to_string(), None).is_ok());
}

#[test]
fn neighbour_paths_do_not_match_and_longest_prefix_wins() {
    let text = json!({"database":"/d/v.db","codex_sessions":"/c","scopes":rules()});
    let config = WatchConfig::parse(&text.to_string(), None).unwrap();
    assert_eq!(config.scope_for(Path::new("/a/project-extra")), None);
    assert_eq!(config.scope_for(Path::new("/a/project-extra/x")), None);
    assert_eq!(config.scope_for(Path::new("/a/project")), Some("p1"));
    assert_eq!(config.scope_for(Path::new("/a/project/x")), Some("p1"));
    assert_eq!(config.scope_for(Path::new("/a/project/sub")), Some("p2"));
    assert_eq!(
        config.scope_for(Path::new("/a/project/sub/y/z")),
        Some("p2")
    );
    assert_eq!(config.scope_for(Path::new("/a/project/subway")), Some("p1"));
    // Kein globaler Ausweichbereich und keine relativen oder unnormalisierten Pfade.
    assert_eq!(config.scope_for(Path::new("/anderswo")), None);
    assert_eq!(config.scope_for(Path::new("a/project")), None);
    assert_eq!(config.scope_for(Path::new("/a/project/../geheim")), None);
}

#[test]
fn invalid_configs_are_rejected() {
    let cases = [
        json!({"database":"v.db","codex_sessions":"/c","scopes":rules()}),
        json!({"database":"/d/v.db","codex_sessions":"c","scopes":rules()}),
        json!({"database":"/d/v.db","codex_sessions":"/c","scopes":[]}),
        json!({"database":"/d/v.db","codex_sessions":"/c","scopes":[{"cwd":"rel","scope":"p"}]}),
        json!({"database":"/d/v.db","codex_sessions":"/c","scopes":[{"cwd":"/a/../b","scope":"p"}]}),
        json!({"database":"/d/v.db","codex_sessions":"/c","scopes":[{"cwd":"/a","scope":" "}]}),
        json!({"database":"/d/v.db","codex_sessions":"/c","days":0,"scopes":rules()}),
        json!({"database":"/d/v.db","codex_sessions":"/c","days":367,"scopes":rules()}),
        json!({"database":"/d/v.db","codex_sessions":"/c","scopes":rules(),"extra":1}),
        json!({"database":"/d/v.db","scopes":rules()}),
    ];
    for case in cases {
        assert!(
            WatchConfig::parse(&case.to_string(), None).is_err(),
            "angenommen: {case}"
        );
    }
    assert!(WatchConfig::parse("kein json", None).is_err());
}

#[test]
fn defaults_for_root_and_days_come_from_home() {
    let text = json!({"database":"/d/v.db","scopes":rules()}).to_string();
    let config = WatchConfig::parse(&text, Some(Path::new("/home/test"))).unwrap();
    assert_eq!(
        config.codex_sessions(),
        Path::new("/home/test/.codex/sessions")
    );
    assert_eq!(config.days(), 7);
    assert_eq!(config.database(), Path::new("/d/v.db"));
}

#[test]
fn date_arithmetic_crosses_month_and_year_boundaries() {
    let date = CivilDate::new(2026, 3, 1).unwrap();
    assert_eq!(date.add_days(-1), CivilDate::new(2026, 2, 28).unwrap());
    assert_eq!(
        CivilDate::new(2024, 3, 1).unwrap().add_days(-1),
        CivilDate::new(2024, 2, 29).unwrap()
    );
    assert_eq!(
        CivilDate::new(2026, 1, 1).unwrap().add_days(-1),
        CivilDate::new(2025, 12, 31).unwrap()
    );
    assert_eq!(date.relative_dir(), Path::new("2026/03/01"));
    assert!(CivilDate::new(2026, 2, 30).is_none());
}

#[test]
fn assigned_sources_are_imported_into_their_scopes() {
    let t = Temp::new();
    t.store();
    let day = t.day(today());
    rollout(
        &day,
        "rollout-a.jsonl",
        "s-a",
        "/a/project/x",
        &["Apfelkuchen"],
    );
    rollout(
        &day,
        "rollout-b.jsonl",
        "s-b",
        "/a/project/sub",
        &["Birnenkuchen"],
    );
    rollout(
        &day,
        "rollout-c.jsonl",
        "s-c",
        "/a/project-extra",
        &["Kirschkuchen"],
    );
    let report = run(&t, &t.config(rules(), 7));
    assert_eq!(report.sources, 3);
    assert_eq!(report.imported, 2);
    assert_eq!(report.added, 2);
    assert_eq!(report.unassigned, 1);
    assert_eq!(report.failed, 0);
    assert_eq!(found(&t, "p1", "Apfelkuchen"), 1);
    assert_eq!(found(&t, "p2", "Birnenkuchen"), 1);
    assert_eq!(found(&t, "p1", "Birnenkuchen"), 0);
    // Nicht zugeordnete Quellen hinterlassen keinen Importstand, auch nicht in global.
    assert_eq!(found(&t, "global", "Kirschkuchen"), 0);
    assert_eq!(t.store().history_status("global").unwrap().sources.len(), 0);
    let hit = &t.store().history_search("p1", "Apfelkuchen", 1).unwrap()[0];
    assert_eq!(hit.tool, "codex");
}

#[test]
fn appended_lines_are_imported_once_over_repeated_runs() {
    let t = Temp::new();
    t.store();
    let day = t.day(today());
    let path = rollout(
        &day,
        "rollout-a.jsonl",
        "s-a",
        "/a/project",
        &["eins", "zwei"],
    );
    let config = t.config(rules(), 7);
    let first = run(&t, &config);
    assert_eq!((first.imported, first.added, first.skipped), (1, 2, 0));
    let mut file = OpenOptions::new().append(true).open(&path).unwrap();
    writeln!(file, "{}", user("s-a-neu", "drei")).unwrap();
    let second = run(&t, &config);
    assert_eq!((second.imported, second.added, second.skipped), (1, 1, 0));
    let third = run(&t, &config);
    assert_eq!((third.imported, third.added, third.skipped), (0, 0, 1));
    assert_eq!(t.store().history_status("p1").unwrap().messages, 3);
}

#[test]
fn broken_source_does_not_block_other_sources() {
    let t = Temp::new();
    t.store();
    let day = t.day(today());
    // Nachricht ohne Inhaltsliste: unbekannte Struktur, die Datei hält an.
    let broken = [
        meta("s-x", "/a/project"),
        json!({"timestamp":STAMP,"type":"event_msg","payload":{"type":"item_completed",
            "item":{"type":"UserMessage","id":"x","client_id":"c","content":"kein Array"}}}),
    ];
    fs::write(day.join("rollout-0-kaputt.jsonl"), lines(&broken)).unwrap();
    // Erste Zeile ohne session_meta: Bereich nicht bestimmbar.
    fs::write(
        day.join("rollout-1-ohne-meta.jsonl"),
        lines(&[user("y", "z")]),
    )
    .unwrap();
    rollout(
        &day,
        "rollout-2-gut.jsonl",
        "s-g",
        "/a/project",
        &["Zwetschge"],
    );
    let report = run(&t, &t.config(rules(), 7));
    assert_eq!(report.sources, 3);
    assert_eq!(report.failed, 2);
    assert_eq!(report.imported, 1);
    assert_eq!(report.errors.len(), 2);
    assert!(
        report
            .errors
            .iter()
            .all(|e| !e.error.contains("kein Array"))
    );
    assert_eq!(found(&t, "p1", "Zwetschge"), 1);
    // Der Importfehler steht im Status des zugeordneten Bereichs.
    let status = t.store().history_status("p1").unwrap();
    assert_eq!(status.failed, 1);
}

#[cfg(unix)]
#[test]
fn symlinks_are_never_followed() {
    use std::os::unix::fs::symlink;
    let t = Temp::new();
    t.store();
    let outside = t.0.join("draussen");
    fs::create_dir(&outside).unwrap();
    let target = rollout(
        &outside,
        "rollout-x.jsonl",
        "s-o",
        "/a/project",
        &["Fremdtext"],
    );
    let day = t.day(today());
    symlink(&target, day.join("rollout-link.jsonl")).unwrap();
    // Tagesordner als Link nach draußen.
    let yesterday = today().add_days(-1).relative_dir();
    let month = t.root().join(yesterday.parent().unwrap());
    fs::create_dir_all(&month).unwrap();
    symlink(&outside, t.root().join(&yesterday)).unwrap();
    let report = run(&t, &t.config(rules(), 7));
    assert_eq!(report.sources, 0);
    assert_eq!(report.ignored, 1);
    assert_eq!(found(&t, "p1", "Fremdtext"), 0);
}

#[cfg(unix)]
#[test]
fn symlinked_root_is_rejected() {
    use std::os::unix::fs::symlink;
    let t = Temp::new();
    t.store();
    let real = t.0.join("echt");
    fs::create_dir(&real).unwrap();
    symlink(&real, t.root()).unwrap();
    assert!(
        t.store()
            .watch_codex_history(&t.config(rules(), 7), today())
            .is_err()
    );
}

#[test]
fn compressed_and_other_files_are_ignored() {
    let t = Temp::new();
    t.store();
    let day = t.day(today());
    rollout(
        &day,
        "rollout-z.jsonl.zst",
        "s-z",
        "/a/project",
        &["Komprimiert"],
    );
    rollout(&day, "anders.jsonl", "s-n", "/a/project", &["Anders"]);
    fs::create_dir(day.join("rollout-ordner.jsonl")).unwrap();
    let report = run(&t, &t.config(rules(), 7));
    assert_eq!(report.sources, 0);
    assert_eq!(report.ignored, 3);
    assert_eq!(found(&t, "p1", "Komprimiert"), 0);
    assert_eq!(found(&t, "p1", "Anders"), 0);
}

#[test]
fn date_folders_outside_the_window_are_ignored() {
    let t = Temp::new();
    t.store();
    // Fenster bei 7 Tagen: 2026-02-22 bis 2026-03-02.
    let inside = t.day(today().add_days(-7));
    let tomorrow = t.day(today().add_days(1));
    let old = t.day(today().add_days(-8));
    let future = t.day(today().add_days(2));
    rollout(
        &inside,
        "rollout-a.jsonl",
        "s-a",
        "/a/project",
        &["Innerhalb"],
    );
    rollout(
        &tomorrow,
        "rollout-b.jsonl",
        "s-b",
        "/a/project",
        &["Morgen"],
    );
    rollout(&old, "rollout-c.jsonl", "s-c", "/a/project", &["Veraltet"]);
    rollout(
        &future,
        "rollout-d.jsonl",
        "s-d",
        "/a/project",
        &["Zukunft"],
    );
    fs::create_dir_all(t.root().join("notizen")).unwrap();
    let report = run(&t, &t.config(rules(), 7));
    assert_eq!(report.sources, 2);
    assert_eq!(found(&t, "p1", "Innerhalb"), 1);
    assert_eq!(found(&t, "p1", "Morgen"), 1);
    assert_eq!(found(&t, "p1", "Veraltet"), 0);
    assert_eq!(found(&t, "p1", "Zukunft"), 0);
}

#[test]
fn incomplete_first_line_waits_without_error() {
    let t = Temp::new();
    t.store();
    let day = t.day(today());
    let partial = meta("s-w", "/a/project").to_string();
    fs::write(day.join("rollout-w.jsonl"), &partial[..partial.len() - 3]).unwrap();
    let report = run(&t, &t.config(rules(), 7));
    assert_eq!((report.sources, report.skipped, report.failed), (1, 1, 0));
}

#[test]
fn missing_root_reads_nothing_and_reports_it() {
    let t = Temp::new();
    t.store();
    let report = run(&t, &t.config(rules(), 7));
    assert!(report.root_missing);
    assert_eq!(report.sources, 0);
}

#[test]
fn second_lock_is_refused_until_the_first_is_released() {
    let t = Temp::new();
    let path = t.0.join("history.json");
    fs::write(&path, "{}").unwrap();
    let first = try_watch_lock(&path).unwrap();
    assert!(first.is_some());
    assert!(try_watch_lock(&path).unwrap().is_none());
    drop(first);
    assert!(try_watch_lock(&path).unwrap().is_some());
}
