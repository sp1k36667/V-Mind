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
    Ok(store.read_snapshot(|store| {
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
    })?)
}

/// Gespeicherte Angabe als eine Markdown-Zeile: Leerraum zusammenziehen und Zeichen
/// maskieren, mit denen ein Text Links, Hervorhebungen oder Code vortäuschen könnte.
fn line(text: &str) -> String {
    let mut out = String::new();
    for c in text
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .chars()
    {
        if matches!(
            c,
            '\\' | '`' | '*' | '_' | '[' | ']' | '<' | '>' | '#' | '|' | '!'
        ) {
            out.push('\\');
        }
        out.push(c);
    }
    out
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
        Some(r) if r.outcome == "failed" => format!(
            "WARNUNG: letzter Prüflauf fehlgeschlagen am {}; Eintrag bleibt als validiert markiert, ist aktuell nicht erneut bestätigt",
            day(&r.created_at)
        ),
        Some(r) if r.outcome == "error" => format!(
            "WARNUNG: letzter Prüflauf mit Ausführungsfehler am {}; keine neue Aussage zur Gültigkeit",
            day(&r.created_at)
        ),
        Some(r) => format!("letzter Prüflauf: {} am {}", r.outcome, day(&r.created_at)),
    }
}

pub fn markdown(report: &Report) -> String {
    let r = &report.resume;
    let mut out = vec![
        format!("# Projektbericht: {}", line(&r.scope)),
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
        format!(
            "## Aufgaben ({} von {}; bis 20 offene, bis 5 zuletzt erledigte)",
            r.tasks.len(),
            r.task_count
        ),
        String::new(),
    ];
    let mut tasks: Vec<_> = r.tasks.iter().collect();
    tasks.sort_by_key(|t| status_rank(t.task_status.as_deref()));
    if tasks.is_empty() {
        out.push("Keine Aufgaben gespeichert.".into());
    }
    for t in tasks {
        out.push(format!(
            "- **{}** {}: {}",
            line(t.task_status.as_deref().unwrap_or("?")),
            line(t.task_key.as_deref().unwrap_or("?")),
            line(&t.body)
        ));
    }
    out.extend([
        String::new(),
        format!(
            "## Letzte Entscheidungen ({} von höchstens 5, neueste zuerst; ältere mit journal)",
            r.decisions.len()
        ),
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
            "## Geprüftes Wissen ({} von {}, neueste zuerst)",
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
        format!(
            "## Ungeprüfte Vorschläge ({} von {})",
            report.pending.len(),
            report.stats.pending
        ),
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
        format!(
            "## Beobachtete Werkzeugaufrufe (nicht geprüft; letzte {} Sitzungen, {} Aufrufe insgesamt)",
            r.observed_sessions.len(),
            r.observation_count
        ),
        String::new(),
    ]);
    if r.observed_sessions.is_empty() {
        out.push("Keine Beobachtungen gespeichert.".into());
    }
    for l in crate::observed_lines(&r.observed_sessions) {
        // Sitzungs-IDs und Pfade stammen vom Host; wie alle Werte maskieren.
        out.push(format!("- {}", line(l.trim_start_matches("- "))));
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
        let blocked = text.find("- **blocked** gpu: GPU Index").unwrap();
        assert!(blocked < text.find("- **done** docs: Doku").unwrap());
        let knowledge = text.find("## Geprüftes Wissen (1 von 1,").unwrap();
        let pending = text.find("## Ungeprüfte Vorschläge (1 von 1)").unwrap();
        let validated_entry = text.find("Leere DB → Migration").unwrap();
        let pending_entry = text.find("Vermutung → ungeklärt").unwrap();
        assert!(knowledge < validated_entry && validated_entry < pending);
        assert!(pending < pending_entry);
        assert!(text.contains("Bestätigt von Prüfer: Test bestanden. kein Prüfbefehl ausgeführt."));
        assert!(text.contains("noch nicht bestätigt"));
    }

    #[test]
    fn stored_text_cannot_inject_links_code_or_headings() {
        let s = MemoryStore::in_memory().unwrap();
        s.journal(
            "p",
            "task",
            Some("in_progress"),
            Some("open"),
            "[klick](http://x) `code`\n# Kopf",
            "T",
        )
        .unwrap();
        let text = markdown(&build(&s, "p").unwrap());
        assert!(text.contains(r"in\_progress: \[klick\](http://x) \`code\` \# Kopf"));
        assert!(!text.contains("\n# Kopf"));
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
