//! `history-watch` und `history-watch-units` über das echte Programm. HOME und
//! XDG_CONFIG_HOME zeigen immer auf einen Temp-Ordner; kein systemctl, keine echte Konfiguration.
use serde_json::{Value, json};
use std::{
    fs,
    path::{Path, PathBuf},
    process::{Command, Output},
};
use vmind_core::CivilDate;

struct Temp(PathBuf);
impl Temp {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "vmind-cli-watch-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir(&path).unwrap();
        Self(path)
    }
    fn join(&self, name: &str) -> PathBuf {
        self.0.join(name)
    }
    fn home(&self) -> PathBuf {
        self.join("home")
    }
    fn db(&self) -> PathBuf {
        self.join("v.db")
    }
    fn root(&self) -> PathBuf {
        self.home().join(".codex/sessions")
    }
    fn config(&self) -> PathBuf {
        self.join("history.json")
    }
    fn run(&self, args: &[&str]) -> Output {
        Command::new(env!("CARGO_BIN_EXE_vmind"))
            .args(args)
            .env("HOME", self.home())
            .env("XDG_CONFIG_HOME", self.home().join(".config"))
            .env_remove("VMIND_SCOPE")
            .output()
            .unwrap()
    }
    fn json(&self, args: &[&str]) -> Value {
        let mut all = vec!["--json"];
        all.extend(args);
        let out = self.run(&all);
        assert!(
            out.status.success(),
            "{}",
            String::from_utf8_lossy(&out.stderr)
        );
        serde_json::from_slice(&out.stdout).unwrap()
    }
    fn init(&self) {
        fs::create_dir_all(self.home()).unwrap();
        let db = self.db();
        assert!(self.run(&["init", db.to_str().unwrap()]).status.success());
    }
    /// Synthetische Rollout-Datei im heutigen (UTC) Tagesordner.
    fn rollout(&self, name: &str, cwd: &str, text: &str) {
        let dir = self.root().join(CivilDate::today_utc().relative_dir());
        fs::create_dir_all(&dir).unwrap();
        let rows = [
            json!({"timestamp":"2026-01-01T00:00:00Z","type":"session_meta",
                "payload":{"id":name,"cwd":cwd}}),
            json!({"timestamp":"2026-01-01T00:00:01Z","type":"event_msg",
                "payload":{"type":"item_completed","item":{"type":"UserMessage","id":"u",
                "client_id":"c","content":[{"type":"text","text":text}]}}}),
        ];
        let body: String = rows.iter().map(|r| format!("{r}\n")).collect();
        fs::write(dir.join(format!("rollout-{name}.jsonl")), body).unwrap();
    }
    fn write_config(&self, path: &Path) {
        let config = json!({"database":self.db(),"days":2,
            "scopes":[{"cwd":"/a/project","scope":"p"}]});
        fs::write(path, config.to_string()).unwrap();
    }
    fn messages(&self) -> Value {
        let db = self.db();
        self.json(&["--scope", "p", "history-status", db.to_str().unwrap()])["messages"].clone()
    }
}
impl Drop for Temp {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[test]
fn missing_config_reads_no_source() {
    let t = Temp::new();
    t.init();
    t.rollout("a", "/a/project", "Nichtlesen");
    let report = t.json(&["history-watch"]);
    assert_eq!(report["status"], "not_configured");
    let expected = t.home().join(".config/vmind/history.json");
    assert_eq!(report["config"], expected.to_str().unwrap());
    assert_eq!(t.messages(), 0);
    let db = t.db();
    let status = t.json(&["--scope", "p", "history-status", db.to_str().unwrap()]);
    assert_eq!(status["sources"], json!([]));
    // Auch ein ausdrücklich genannter, fehlender Pfad liest nichts und endet ohne Fehler.
    let missing = t.join("fehlt.json");
    let report = t.json(&["history-watch", "--config", missing.to_str().unwrap()]);
    assert_eq!(report["status"], "not_configured");
}

#[test]
fn configured_run_imports_and_repeats_without_duplicates() {
    let t = Temp::new();
    t.init();
    t.rollout("a", "/a/project/x", "Sonnenblume");
    t.rollout("b", "/a/project-extra", "Nachbar");
    // Standardpfad über XDG_CONFIG_HOME.
    let config = t.home().join(".config/vmind/history.json");
    fs::create_dir_all(config.parent().unwrap()).unwrap();
    t.write_config(&config);
    let first = t.json(&["history-watch"]);
    assert_eq!(first["status"], "completed");
    assert_eq!(first["sources"], 2);
    assert_eq!(first["imported"], 1);
    assert_eq!(first["added"], 1);
    assert_eq!(first["unassigned"], 1);
    assert_eq!(first["failed"], 0);
    let second = t.json(&["history-watch"]);
    assert_eq!(
        (second["added"].clone(), second["skipped"].clone()),
        (json!(0), json!(1))
    );
    assert_eq!(t.messages(), 1);
    let text = t.run(&["history-watch"]);
    let text = String::from_utf8_lossy(&text.stdout);
    assert!(text.contains("nicht zugeordnet: 1"), "{text}");
}

#[test]
fn ambiguous_config_is_an_error() {
    let t = Temp::new();
    t.init();
    let config = t.config();
    let text =
        json!({"database":t.db(),"scopes":[{"cwd":"/a","scope":"x"},{"cwd":"/a/","scope":"y"}]});
    fs::write(&config, text.to_string()).unwrap();
    let out = t.run(&["history-watch", "--config", config.to_str().unwrap()]);
    assert!(!out.status.success());
    assert!(String::from_utf8_lossy(&out.stderr).contains("Mehrdeutige Zuordnung"));
}

#[test]
fn second_parallel_run_skips_without_error() {
    let t = Temp::new();
    t.init();
    t.rollout("a", "/a/project", "Gesperrt");
    let config = t.config();
    t.write_config(&config);
    let held = fs::File::open(&config).unwrap();
    held.try_lock().unwrap();
    let report = t.json(&["history-watch", "--config", config.to_str().unwrap()]);
    assert_eq!(report["status"], "locked");
    assert_eq!(t.messages(), 0);
    drop(held);
    let report = t.json(&["history-watch", "--config", config.to_str().unwrap()]);
    assert_eq!(report["status"], "completed");
    assert_eq!(t.messages(), 1);
}

#[test]
fn generated_units_contain_expected_lines_and_are_not_installed() {
    let t = Temp::new();
    fs::create_dir_all(t.home()).unwrap();
    let out = t.run(&[
        "history-watch-units",
        "--config",
        "/pfad mit leer/history.json",
        "--vmind",
        "/opt/v%mind/vmind",
        "--interval",
        "30",
    ]);
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let text = String::from_utf8_lossy(&out.stdout);
    for line in [
        "[Service]",
        "Type=oneshot",
        "ExecStart=\"/opt/v%%mind/vmind\" \"history-watch\" \"--config\" \"/pfad mit leer/history.json\"",
        "[Timer]",
        "OnBootSec=2min",
        "OnUnitActiveSec=30min",
        "Unit=vmind-history-watch.service",
        "WantedBy=timers.target",
    ] {
        assert!(text.lines().any(|l| l == line), "fehlt: {line}\n{text}");
    }
    // Nichts unter HOME angelegt, insbesondere keine systemd-Unit.
    assert!(!t.home().join(".config/systemd").exists());

    let dir = t.join("units");
    fs::create_dir(&dir).unwrap();
    let args = [
        "history-watch-units",
        "--config",
        "/k/history.json",
        "--vmind",
        "/v/vmind",
        "--output",
        dir.to_str().unwrap(),
    ];
    assert!(t.run(&args).status.success());
    let service = fs::read_to_string(dir.join("vmind-history-watch.service")).unwrap();
    let timer = fs::read_to_string(dir.join("vmind-history-watch.timer")).unwrap();
    assert!(
        service
            .contains("ExecStart=\"/v/vmind\" \"history-watch\" \"--config\" \"/k/history.json\"")
    );
    assert!(timer.lines().any(|l| l == "OnUnitActiveSec=15min"));
    // Vorhandene Dateien werden nie überschrieben.
    assert!(!t.run(&args).status.success());
}

#[test]
fn unit_generation_rejects_bad_options() {
    let t = Temp::new();
    fs::create_dir_all(t.home()).unwrap();
    for args in [
        vec!["history-watch-units", "--interval", "0", "--vmind", "/v"],
        vec![
            "history-watch-units",
            "--config",
            "relativ.json",
            "--vmind",
            "/v",
        ],
        vec![
            "history-watch-units",
            "--config",
            "/k\n[Service]",
            "--vmind",
            "/v",
        ],
        vec!["history-watch-units", "--unbekannt", "x"],
    ] {
        assert!(!t.run(&args).status.success(), "angenommen: {args:?}");
    }
}
