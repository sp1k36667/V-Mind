//! Lesbarer Projektbericht für Menschen: zeigt nur gespeicherte Angaben, trennt
//! geprüftes Wissen von ungeprüften Vorschlägen und ändert nichts an der Datenbank.
use serde::Serialize;
use vmind_core::{CheckRun, MemoryStore, Record, Resume, Stats};

/// Höchstens so viele geprüfte Einträge im Bericht; die Gesamtzahl steht dabei.
const REPORT_KNOWLEDGE: usize = 20;

#[derive(Serialize)]
pub struct Knowledge {
    #[serde(flatten)]
    pub record: Record,
    pub last_check_run: Option<CheckRun>,
}

#[derive(Serialize)]
pub struct Report {
    pub resume: Resume,
    pub stats: Stats,
    pub knowledge: Vec<Knowledge>,
    pub pending: Vec<Record>,
}

pub fn build(store: &MemoryStore, scope: &str) -> crate::Result<Report> {
    let mut knowledge = Vec::new();
    for record in store.validated(scope, REPORT_KNOWLEDGE)? {
        let last_check_run = store.check_runs(record.id, 1)?.into_iter().next();
        knowledge.push(Knowledge {
            record,
            last_check_run,
        });
    }
    Ok(Report {
        resume: store.resume(scope, None)?,
        stats: store.stats(scope)?,
        knowledge,
        pending: store.pending(scope)?,
    })
}

/// Zeilenumbrüche und Mehrfachleerzeichen einer Angabe für eine Listenzeile zusammenziehen.
fn line(text: &str) -> String {
    text.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn day(timestamp: &str) -> &str {
    timestamp.get(..10).unwrap_or(timestamp)
}

/// Blockierte und laufende Aufgaben zuerst, erledigte zuletzt.
fn status_rank(status: Option<&str>) -> u8 {
    match status {
        Some("blocked") => 0,
        Some("in_progress") => 1,
        Some("open") => 2,
        Some("done") => 3,
        _ => 4,
    }
}

fn check_note(run: Option<&CheckRun>) -> String {
    match run {
        None => "kein Prüfbefehl ausgeführt".into(),
        Some(r) => format!("letzter Prüflauf: {} am {}", r.outcome, day(&r.created_at)),
    }
}

pub fn markdown(report: &Report) -> String {
    let r = &report.resume;
    let mut out = vec![
        format!("# Projektbericht: {}", r.scope),
        String::new(),
        format!(
            "Aus V-Mind (Schema {}). Enthält nur gespeicherte Angaben. Geprüftes Wissen und \
             ungeprüfte Vorschläge stehen getrennt.",
            report.stats.schema_version
        ),
        String::new(),
        format!(
            "**Ziel:** {}",
            r.goal
                .as_ref()
                .map_or("noch nicht gespeichert".into(), |e| line(&e.body))
        ),
        format!(
            "**Nächster Schritt:** {}",
            r.next_step
                .as_ref()
                .map_or("noch nicht festgelegt".into(), |e| line(&e.body))
        ),
        String::new(),
        format!("## Aufgaben ({} von {})", r.tasks.len(), r.task_count),
        String::new(),
    ];
    let mut tasks: Vec<_> = r.tasks.iter().collect();
    tasks.sort_by_key(|t| status_rank(t.task_status.as_deref()));
    if tasks.is_empty() {
        out.push("Keine Aufgaben gespeichert.".into());
    }
    for t in tasks {
        out.push(format!(
            "- **{}** `{}`: {}",
            t.task_status.as_deref().unwrap_or("?"),
            t.task_key.as_deref().unwrap_or("?"),
            line(&t.body)
        ));
    }
    out.extend([
        String::new(),
        "## Letzte Entscheidungen".into(),
        String::new(),
    ]);
    if r.decisions.is_empty() {
        out.push("Keine Entscheidungen gespeichert.".into());
    }
    for d in &r.decisions {
        out.push(format!(
            "- {} ({}, Quelle: {})",
            line(&d.body),
            day(&d.created_at),
            line(&d.source)
        ));
    }
    out.extend([
        String::new(),
        format!(
            "## Geprüftes Wissen ({} von {})",
            report.knowledge.len(),
            report.stats.validated
        ),
        String::new(),
    ]);
    if report.knowledge.is_empty() {
        out.push("Noch kein geprüftes Wissen.".into());
    }
    for k in &report.knowledge {
        let m = &k.record;
        out.push(format!(
            "- **#{}** {} → {}  \n  Quelle: {}. Bestätigt von {}: {}. {}.",
            m.id,
            line(&m.problem),
            line(&m.solution),
            line(&m.source),
            m.validated_by.as_deref().map_or("?".into(), line),
            m.evidence.as_deref().map_or("?".into(), line),
            check_note(k.last_check_run.as_ref())
        ));
    }
    out.extend([
        String::new(),
        format!("## Ungeprüfte Vorschläge ({})", report.stats.pending),
        String::new(),
    ]);
    if report.pending.is_empty() {
        out.push("Keine offenen Vorschläge.".into());
    }
    for p in &report.pending {
        out.push(format!(
            "- **#{}** {} → {} (Quelle: {}; noch nicht bestätigt)",
            p.id,
            line(&p.problem),
            line(&p.solution),
            line(&p.source)
        ));
    }
    out.extend([
        String::new(),
        "## Umfang".into(),
        String::new(),
        format!(
            "{} Projektereignisse, {} zurückgezogene Einträge. Vollständige Historie mit \
             `journal`, einzelne Einträge mit `show`.",
            r.total_events, report.stats.invalidated
        ),
    ]);
    out.join("\n")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn store() -> MemoryStore {
        let s = MemoryStore::in_memory().unwrap();
        s.journal("p", "goal", None, None, "Release 1.0", "Nutzer")
            .unwrap();
        s.journal("p", "task", Some("docs"), Some("done"), "Doku", "T")
            .unwrap();
        s.journal("p", "task", Some("gpu"), Some("blocked"), "GPU\nIndex", "T")
            .unwrap();
        s.journal("p", "decision", None, None, "SQLite bleibt", "Nutzer")
            .unwrap();
        s.journal("p", "next_step", None, None, "Tests schreiben", "T")
            .unwrap();
        let id = s
            .remember_scoped("p", "error_solution", "Leere DB", "Migration", "Test")
            .unwrap();
        s.validate(id, "Prüfer", "Test bestanden").unwrap();
        s.remember_scoped("p", "long_term", "Vermutung", "ungeklärt", "Modell")
            .unwrap();
        s
    }

    #[test]
    fn report_separates_validated_from_pending_and_orders_blocked_tasks_first() {
        let text = markdown(&build(&store(), "p").unwrap());
        assert!(text.starts_with("# Projektbericht: p"));
        assert!(text.contains("**Ziel:** Release 1.0"));
        assert!(text.contains("**Nächster Schritt:** Tests schreiben"));
        let blocked = text.find("`gpu`: GPU Index").unwrap();
        assert!(blocked < text.find("`docs`").unwrap());
        let knowledge = text.find("## Geprüftes Wissen (1 von 1)").unwrap();
        let pending = text.find("## Ungeprüfte Vorschläge (1)").unwrap();
        let validated_entry = text.find("Leere DB → Migration").unwrap();
        let pending_entry = text.find("Vermutung → ungeklärt").unwrap();
        assert!(knowledge < validated_entry && validated_entry < pending);
        assert!(pending < pending_entry);
        assert!(text.contains("Bestätigt von Prüfer: Test bestanden. kein Prüfbefehl ausgeführt."));
        assert!(text.contains("noch nicht bestätigt"));
    }

    #[test]
    fn empty_project_reports_missing_data_instead_of_inventing_it() {
        let text = markdown(&build(&MemoryStore::in_memory().unwrap(), "leer").unwrap());
        assert!(text.contains("**Ziel:** noch nicht gespeichert"));
        assert!(text.contains("Keine Aufgaben gespeichert."));
        assert!(text.contains("Noch kein geprüftes Wissen."));
        assert!(text.contains("Keine offenen Vorschläge."));
    }
}
