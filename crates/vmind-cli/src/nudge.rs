//! `vmind nudge DB`: Claude-Code-Hook für UserPromptSubmit. Erinnert bei jeder Eingabe in einer
//! kurzen Zeile an `journal_search` und `recall` und nennt nur Zahlen zum offenen Stand. Nur
//! lesend: Vom Hook wird allein der Ereignisname geprüft, der Prompt-Text wird weder verwendet
//! noch gespeichert noch ausgegeben; gespeicherte Texte erscheinen nicht. Jeder Fehler endet
//! still und erfolgreich, damit der Hook eine Eingabe nie blockiert.
use serde_json::{Value, json};
use std::{io::Read, time::Duration};
use vmind_core::{JournalEntry, MemoryStore, RESUME_OPEN_TASKS, Resume};

const MAX_INPUT_BYTES: u64 = 1024 * 1024;
const BUSY_WAIT: Duration = Duration::from_millis(500);
const EVENT: &str = "UserPromptSubmit";
const REMINDER: &str =
    "V-Mind: Vor der Arbeit journal_search zum Thema und recall für Wissen nutzen.";

fn status(task: &JournalEntry) -> Option<&str> {
    task.task_status.as_deref()
}

/// Hinweis auf offene Arbeit; die Grenze des Snapshots gilt für alle unerledigten Aufgaben.
fn open_work(resume: &Resume) -> Option<String> {
    let shown_open = resume
        .tasks
        .iter()
        .filter(|t| status(t) != Some("done"))
        .count();
    let active = resume
        .tasks
        .iter()
        .filter(|t| matches!(status(t), Some("in_progress" | "blocked")))
        .count();
    let bound = if shown_open >= RESUME_OPEN_TASKS {
        "mindestens "
    } else {
        ""
    };
    let stale = resume.stale_tasks.len();
    let stale_note = (stale > 0).then(|| format!(" (möglicherweise veraltet: {bound}{stale})"));
    (active > 0).then(|| {
        format!(
            "Aufgaben in Arbeit oder blockiert: {bound}{active}{}",
            stale_note.unwrap_or_default()
        )
    })
}

/// Der gespeicherte nächste Schritt liegt vor der neuesten Aufgabenmeldung.
fn next_step_outdated(resume: &Resume) -> bool {
    let newest_task = resume.tasks.iter().map(|t| t.id).max();
    matches!((&resume.next_step, newest_task), (Some(step), Some(task)) if step.id < task)
}

/// Kontextzeile aus festen Wörtern und Zahlen; enthält nie gespeicherte Texte.
fn context(resume: &Resume) -> String {
    let count = |label: &str, total: i64| (total > 0).then(|| format!("{label}: {total}"));
    let parts: Vec<String> = [
        open_work(resume),
        count("Reparaturen ohne Vorschlag", resume.open_repairs.total),
        count("ungeprüfte Einträge", resume.open_hints.total),
        next_step_outdated(resume).then(|| "nächster Schritt möglicherweise überholt".to_owned()),
    ]
    .into_iter()
    .flatten()
    .collect();
    if parts.is_empty() {
        REMINDER.to_owned()
    } else {
        format!("{REMINDER} {}", parts.join("; "))
    }
}

fn answer(db: &str, scope: &str, raw: &[u8]) -> Option<Value> {
    let input: Value = serde_json::from_slice(raw).ok()?;
    if input["hook_event_name"].as_str()? != EVENT {
        return None;
    }
    let store = MemoryStore::open_read_only_waiting(db, BUSY_WAIT).ok()?;
    let resume = store.resume(scope, None).ok()?;
    Some(json!({"hookSpecificOutput": {
        "hookEventName": EVENT,
        "additionalContext": context(&resume)
    }}))
}

pub fn run(db: &str, scope: &str) -> crate::Result<()> {
    let mut raw = Vec::new();
    let read = std::io::stdin()
        .lock()
        .take(MAX_INPUT_BYTES + 1)
        .read_to_end(&mut raw);
    if read.is_err() || raw.len() as u64 > MAX_INPUT_BYTES {
        return Ok(());
    }
    if let Some(answer) = answer(db, scope, &raw) {
        println!("{answer}");
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use vmind_core::StaleTask;

    const SCOPE: &str = "p";
    const SECRET: &str = "GEHEIMER-AUFGABENTEXT";
    /// Obergrenze aus dem Funktionsumfang: eine kurze Zeile von etwa 300 Zeichen.
    const MAX_CONTEXT_CHARS: usize = 300;

    fn store_with_tasks(statuses: &[&str]) -> MemoryStore {
        let store = MemoryStore::in_memory().unwrap();
        for (i, status) in statuses.iter().enumerate() {
            let key = format!("{SECRET}-{i}");
            store
                .journal(SCOPE, "task", Some(&key), Some(status), SECRET, SECRET)
                .unwrap();
        }
        store
    }

    fn stale(id: i64) -> StaleTask {
        StaleTask {
            id,
            task_key: Some(SECRET.into()),
            task_status: Some("in_progress".into()),
            age_days: 3,
        }
    }

    fn next_step(store: &MemoryStore) {
        store
            .journal(SCOPE, "next_step", None, None, SECRET, SECRET)
            .unwrap();
    }

    #[test]
    fn only_the_reminder_appears_without_open_work() {
        let store = store_with_tasks(&["done"]);
        let text = context(&store.resume(SCOPE, None).unwrap());
        assert_eq!(text, REMINDER);
    }

    #[test]
    fn counts_only_in_progress_and_blocked_tasks() {
        let store = store_with_tasks(&["in_progress", "blocked", "open", "done"]);
        let text = context(&store.resume(SCOPE, None).unwrap());
        assert!(text.contains("in Arbeit oder blockiert: 2"), "{text}");
        assert!(!text.contains("mindestens"), "{text}");
        assert!(!text.contains("veraltet"), "{text}");
    }

    #[test]
    fn says_at_least_when_the_snapshot_limit_is_reached() {
        let store = store_with_tasks(&["in_progress"; RESUME_OPEN_TASKS + 2]);
        let mut resume = store.resume(SCOPE, None).unwrap();
        resume.stale_tasks.push(stale(1));
        let text = context(&resume);
        assert!(
            text.contains(&format!("blockiert: mindestens {RESUME_OPEN_TASKS}")),
            "{text}"
        );
        assert!(text.contains("veraltet: mindestens 1"), "{text}");
    }

    #[test]
    fn says_at_least_when_other_open_tasks_fill_the_snapshot() {
        // Die Grenze gilt für alle unerledigten Aufgaben; ältere könnten in Arbeit sein.
        let mut statuses = vec!["open"; RESUME_OPEN_TASKS - 1];
        statuses.push("blocked");
        let store = store_with_tasks(&statuses);
        let text = context(&store.resume(SCOPE, None).unwrap());
        assert!(text.contains("blockiert: mindestens 1"), "{text}");
    }

    #[test]
    fn names_stale_tasks_repairs_and_hints_only_when_present() {
        let store = store_with_tasks(&["in_progress", "blocked"]);
        let mut resume = store.resume(SCOPE, None).unwrap();
        let without = context(&resume);
        assert!(!without.contains("Reparaturen"), "{without}");
        assert!(!without.contains("ungeprüfte"), "{without}");
        resume.stale_tasks.push(stale(1));
        resume.open_repairs.total = 4;
        resume.open_hints.total = 7;
        let text = context(&resume);
        assert!(text.contains("veraltet: 1"), "{text}");
        assert!(text.contains("Reparaturen ohne Vorschlag: 4"), "{text}");
        assert!(text.contains("ungeprüfte Einträge: 7"), "{text}");
    }

    #[test]
    fn flags_a_next_step_older_than_the_newest_task() {
        let store = store_with_tasks(&["done"]);
        next_step(&store);
        let current = context(&store.resume(SCOPE, None).unwrap());
        assert!(!current.contains("überholt"), "{current}");
        store
            .journal(SCOPE, "task", Some("neu"), Some("done"), "x", "y")
            .unwrap();
        let outdated = context(&store.resume(SCOPE, None).unwrap());
        assert!(
            outdated.contains("nächster Schritt möglicherweise überholt"),
            "{outdated}"
        );
    }

    #[test]
    fn no_next_step_is_never_flagged_as_outdated() {
        let store = store_with_tasks(&["in_progress"]);
        let text = context(&store.resume(SCOPE, None).unwrap());
        assert!(!text.contains("überholt"), "{text}");
    }

    #[test]
    fn stays_one_short_line_without_stored_text() {
        let store = store_with_tasks(&["in_progress"; RESUME_OPEN_TASKS + 2]);
        next_step(&store);
        store
            .journal(SCOPE, "task", Some("neu"), Some("blocked"), SECRET, SECRET)
            .unwrap();
        let mut resume = store.resume(SCOPE, None).unwrap();
        resume
            .stale_tasks
            .extend((0..RESUME_OPEN_TASKS as i64).map(stale));
        resume.open_repairs.total = i64::MAX;
        resume.open_hints.total = i64::MAX;
        let text = context(&resume);
        assert!(!text.contains(SECRET), "{text}");
        assert!(!text.contains('\n'), "{text}");
        assert!(text.chars().count() <= MAX_CONTEXT_CHARS, "{text}");
    }
}
