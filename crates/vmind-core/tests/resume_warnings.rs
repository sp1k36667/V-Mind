use vmind_core::MemoryStore;

struct Temp(std::path::PathBuf);
impl Temp {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "vmind-resume-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&path).unwrap();
        Self(path)
    }
}
impl Drop for Temp {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

/// Aufgabe anlegen und ihren Zeitstempel direkt in der Datei setzen (SQL-Ausdruck).
fn task(path: &std::path::Path, s: &MemoryStore, key: &str, status: &str, created: &str) -> i64 {
    let id = s
        .journal("p", "task", Some(key), Some(status), key, "Test")
        .unwrap();
    rusqlite::Connection::open(path)
        .unwrap()
        .execute(
            &format!("UPDATE project_journal SET created_at={created} WHERE id=?1"),
            [id],
        )
        .unwrap();
    id
}
fn days_ago(days: f64) -> String {
    format!(
        "strftime('%Y-%m-%dT%H:%M:%fZ','now','-{} seconds')",
        (days * 86400.0) as i64
    )
}

#[test]
fn tasks_open_for_two_full_days_are_flagged_without_changing_their_status() {
    let temp = Temp::new();
    let path = temp.0.join("r.db");
    let s = MemoryStore::open(&path).unwrap();
    let alt = task(&path, &s, "alt", "in_progress", &days_ago(3.2));
    let frisch = task(&path, &s, "frisch", "in_progress", &days_ago(1.5));
    let blockiert = task(&path, &s, "blockiert", "blocked", &days_ago(2.1));
    task(&path, &s, "erledigt", "done", &days_ago(10.0));
    task(&path, &s, "offen", "open", &days_ago(10.0));
    let r = s.resume("p", None).unwrap();
    let mut stale: Vec<(i64, i64)> = r.stale_tasks.iter().map(|t| (t.id, t.age_days)).collect();
    stale.sort();
    let mut expected = vec![(alt, 3), (blockiert, 2)];
    expected.sort();
    assert_eq!(stale, expected);
    assert!(
        !r.stale_tasks.iter().any(|t| t.id == frisch),
        "1,5 Tage sind keine zwei vollen Tage"
    );
    assert_eq!(r.stale_tasks.len(), 2, "done und open werden nie markiert");
    let status = s
        .resume("p", None)
        .unwrap()
        .tasks
        .iter()
        .find(|t| t.id == alt)
        .unwrap()
        .task_status
        .clone();
    assert_eq!(
        status.as_deref(),
        Some("in_progress"),
        "Status bleibt unverändert"
    );
}

#[test]
fn odd_timestamps_never_fail_resume_or_warn_falsely() {
    let temp = Temp::new();
    let path = temp.0.join("r.db");
    let s = MemoryStore::open(&path).unwrap();
    let altes_format = task(
        &path,
        &s,
        "altformat",
        "in_progress",
        "datetime('now','-5 days')",
    );
    task(&path, &s, "kaputt", "in_progress", "'kein Datum'");
    task(&path, &s, "leer", "in_progress", "''");
    task(
        &path,
        &s,
        "zukunft",
        "in_progress",
        "strftime('%Y-%m-%dT%H:%M:%fZ','now','+3 days')",
    );
    let r = s.resume("p", None).unwrap();
    let ids: Vec<i64> = r.stale_tasks.iter().map(|t| t.id).collect();
    assert_eq!(
        ids,
        [altes_format],
        "nur der gültige alte Zeitstempel warnt"
    );
    assert_eq!(r.stale_tasks[0].age_days, 5);
}

#[test]
fn open_hints_count_active_pending_entries_of_the_exact_scope() {
    let s = MemoryStore::in_memory().unwrap();
    let add = |scope: &str| {
        s.remember_scoped(scope, "long_term", "Vorschlag", "Lösung", "Test")
            .unwrap()
    };
    let a = add("p");
    let b = add("p");
    let c = add("p");
    let d = add("p");
    let zurueck = add("p");
    s.invalidate(zurueck, "Prüfer", "falsch").unwrap();
    s.validate(a, "Prüfer", "Test").unwrap();
    add("global");
    add("anderes");
    let hints = s.resume("p", None).unwrap().open_hints;
    assert_eq!(
        hints.total, 3,
        "nur aktive pending im Bereich p, ohne global"
    );
    assert_eq!(hints.newest_ids, [d, c, b]);
    let leer = s.resume("leer", None).unwrap().open_hints;
    assert_eq!((leer.total, leer.newest_ids.len()), (0, 0));
}
