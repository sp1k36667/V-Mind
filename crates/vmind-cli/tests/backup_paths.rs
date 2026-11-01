use std::{fs, process::Command};

#[cfg(unix)]
#[test]
fn backup_treats_its_destination_as_a_file_not_as_an_overwriting_sqlite_uri() {
    let dir = std::env::temp_dir().join(format!(
        "vmind-uri-backup-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    fs::create_dir(&dir).unwrap();
    let source = dir.join("source.db");
    let protected = dir.join("protected.db");
    let cli = |args: &[&str]| {
        let output = Command::new(env!("CARGO_BIN_EXE_vmind"))
            .current_dir(&dir)
            .args(args)
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
    };
    cli(&["init", source.to_str().unwrap()]);
    cli(&[
        "add",
        source.to_str().unwrap(),
        "long_term",
        "Quellkopie",
        "Quelle",
        "Fixture",
    ]);
    cli(&["init", protected.to_str().unwrap()]);
    cli(&[
        "add",
        protected.to_str().unwrap(),
        "long_term",
        "Geschützter Bestand",
        "Original",
        "Fixture",
    ]);
    let before = fs::read(&protected).unwrap();
    // This is a legal Unix filename. SQLite must not reinterpret it as protected.db.
    let target = "file:protected.db?mode=rw";
    cli(&["backup", source.to_str().unwrap(), target]);
    assert!(
        fs::read(&protected).unwrap() == before,
        "Existing URI target must remain unchanged"
    );
    assert!(
        fs::read(dir.join(target))
            .unwrap()
            .starts_with(b"SQLite format 3\0")
    );
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn ordinary_backup_paths_with_spaces_and_unicode_work_without_external_tools() {
    let dir = std::env::temp_dir().join(format!(
        "vmind-portable-backup-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    fs::create_dir(&dir).unwrap();
    let call = |args: &[&str]| {
        let out = Command::new(env!("CARGO_BIN_EXE_vmind"))
            .current_dir(&dir)
            .args(args)
            .output()
            .unwrap();
        assert!(
            out.status.success(),
            "{}",
            String::from_utf8_lossy(&out.stderr)
        );
        out
    };
    call(&["init", "Quelle mit ä.db"]);
    call(&[
        "add",
        "Quelle mit ä.db",
        "long_term",
        "Original",
        "Bewahren",
        "Fixture",
    ]);
    call(&["backup", "Quelle mit ä.db", "Sicherung mit ü.db"]);
    let report = call(&["--json", "doctor", "Sicherung mit ü.db"]);
    let report: serde_json::Value = serde_json::from_slice(&report.stdout).unwrap();
    assert_eq!(report["healthy"], true);
    let shown = call(&["--json", "show", "Sicherung mit ü.db", "1"]);
    let shown: serde_json::Value = serde_json::from_slice(&shown.stdout).unwrap();
    assert_eq!(shown["memory"]["problem"], "Original");
    fs::remove_dir_all(dir).unwrap();
}

#[cfg(unix)]
#[test]
fn cli_uri_shaped_names_persist_across_processes_instead_of_creating_memory_databases() {
    let dir = std::env::temp_dir().join(format!(
        "vmind-literal-db-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    fs::create_dir(&dir).unwrap();
    let name = "file:project.db?mode=memory";
    for args in [
        vec!["init", name],
        vec!["add", name, "long_term", "Persistiert", "Datei", "Fixture"],
    ] {
        let out = Command::new(env!("CARGO_BIN_EXE_vmind"))
            .current_dir(&dir)
            .args(args)
            .output()
            .unwrap();
        assert!(
            out.status.success(),
            "{}",
            String::from_utf8_lossy(&out.stderr)
        );
    }
    let out = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .current_dir(&dir)
        .args(["--json", "show", name, "1"])
        .output()
        .unwrap();
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let shown: serde_json::Value = serde_json::from_slice(&out.stdout).unwrap();
    assert_eq!(shown["memory"]["problem"], "Persistiert");
    use std::io::Write;
    let mut server = Command::new(env!("CARGO_BIN_EXE_vmind"))
        .current_dir(&dir)
        .args(["serve", name])
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .unwrap();
    server
        .stdin
        .take()
        .unwrap()
        .write_all(b"{\"op\":\"get\",\"memory_id\":1}\n")
        .unwrap();
    let output = server.wait_with_output().unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let response: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(response["data"]["memory"]["problem"], "Persistiert");

    assert!(
        fs::read(dir.join(name))
            .unwrap()
            .starts_with(b"SQLite format 3\0")
    );
    fs::remove_dir_all(dir).unwrap();
}
