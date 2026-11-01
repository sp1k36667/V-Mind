#![cfg(unix)]
use std::{fs, process::Command};

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
