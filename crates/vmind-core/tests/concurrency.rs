use std::sync::mpsc;
use std::time::Duration;
use vmind_core::MemoryStore;

struct Temp(std::path::PathBuf);
impl Temp {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "vmind-busy-{}-{}",
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

/// Ein anderer Prozess hält die Schreibsperre länger als busy_timeout (5 s). Der Schreibbefehl
/// muss nach begrenzter Wiederholung gelingen und genau einmal gespeichert sein.
#[test]
fn write_waits_out_a_lock_held_longer_than_busy_timeout_without_duplicates() {
    let temp = Temp::new();
    let path = temp.0.join("busy.db");
    let store = MemoryStore::open(&path).unwrap();
    let conversation = store.create_conversation("p", "Sperre").unwrap();
    let (bereit, warten) = mpsc::channel();
    let sperre = {
        let path = path.clone();
        std::thread::spawn(move || {
            let conn = rusqlite::Connection::open(&path).unwrap();
            conn.execute_batch("BEGIN IMMEDIATE").unwrap();
            bereit.send(()).unwrap();
            std::thread::sleep(Duration::from_millis(6500));
            conn.execute_batch("COMMIT").unwrap();
        })
    };
    warten.recv().unwrap();
    let id = store
        .append_message(&conversation, "assistant", "nach der Sperre")
        .unwrap();
    sperre.join().unwrap();
    let messages = store.messages(&conversation, 0, 10).unwrap();
    assert_eq!(messages.len(), 1);
    assert_eq!(messages[0].id, id);
    let entry = store
        .journal("p", "note", None, None, "Notiz nach Sperre", "Test")
        .unwrap();
    assert!(entry > 0);
}

/// Zwei Verbindungen schreiben gleichzeitig; jede Rückmeldung entspricht genau einer Zeile.
#[test]
fn concurrent_writers_store_each_message_exactly_once() {
    let temp = Temp::new();
    let path = temp.0.join("parallel.db");
    let conversation = MemoryStore::open(&path)
        .unwrap()
        .create_conversation("p", "Parallel")
        .unwrap();
    let schreiber: Vec<_> = ["A", "B"]
        .into_iter()
        .map(|name| {
            let (path, conversation) = (path.clone(), conversation.clone());
            std::thread::spawn(move || {
                let store = MemoryStore::open_existing(&path).unwrap();
                (0..300)
                    .map(|i| {
                        store
                            .append_message(&conversation, "assistant", &format!("{name}-{i:03}"))
                            .unwrap()
                    })
                    .collect::<Vec<_>>()
            })
        })
        .collect();
    let mut ids: Vec<i64> = schreiber
        .into_iter()
        .flat_map(|s| s.join().unwrap())
        .collect();
    ids.sort_unstable();
    ids.dedup();
    assert_eq!(ids.len(), 600);
    let store = MemoryStore::open_existing(&path).unwrap();
    let mut gespeichert = Vec::new();
    let mut nach = 0;
    loop {
        let seite = store.messages(&conversation, nach, 100).unwrap();
        let Some(letzte) = seite.last() else { break };
        nach = letzte.id;
        gespeichert.extend(seite.into_iter().map(|m| m.content));
    }
    gespeichert.sort();
    let mut erwartet: Vec<String> = ["A", "B"]
        .iter()
        .flat_map(|n| (0..300).map(move |i| format!("{n}-{i:03}")))
        .collect();
    erwartet.sort();
    assert_eq!(gespeichert, erwartet);
}
