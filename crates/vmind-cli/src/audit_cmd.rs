//! `audit-secrets DB`: rein lesender Bericht über bekannte Geheimnisformate. Gibt nie
//! Feldwerte aus; Exit 0 auch mit Funden, Fehler nur, wenn nicht durchsucht werden konnte.
use crate::{Result, emit};
use vmind_core::{AuditReport, audit_secrets};

fn human(report: &AuditReport) -> String {
    let rows: i64 = report.scanned.iter().map(|t| t.rows).sum();
    let mut lines = vec![
        format!("Hinweis: {}", report.notice),
        format!(
            "Durchsucht: Schema {}, {} Tabellen, {rows} Zeilen, alle Bereiche.",
            report.schema_version,
            report.scanned.len()
        ),
    ];
    if report.findings.is_empty() {
        lines.push("Keine bekannten Geheimnisformate gefunden.".into());
        return lines.join("\n");
    }
    let uncertain = report.findings.iter().filter(|f| !f.certain).count();
    lines.push(format!(
        "{} Funde, davon {uncertain} unsicher:",
        report.findings.len()
    ));
    lines.extend(report.findings.iter().map(|f| {
        let mut line = format!(
            "- {} #{} Feld {}: {}{}",
            f.table,
            f.row_id,
            f.field,
            f.label,
            if f.certain { "" } else { " (unsicher)" }
        );
        if let Some(id) = f
            .memory_id
            .filter(|&id| f.table != "memories" || id != f.row_id)
        {
            line.push_str(&format!(", Eintrag #{id}"));
        }
        if let Some(row) = f.conversation_row {
            line.push_str(&format!(", Gespräch rowid {row}"));
        }
        line
    }));
    lines.join("\n")
}

pub fn run(db: &str, json_mode: bool) -> Result<()> {
    // SQLite errors may contain schema object names or file paths from the database.
    // Do not echo potentially sensitive values on this content-redacting command.
    let report = audit_secrets(db).map_err(|_| std::io::Error::other(
        "Audit konnte die Datenbank nicht vollständig prüfen. Datei, unterstütztes Schema und Lesbarkeit prüfen; kein vollständiges Ergebnis.",
    ))?;
    let text = human(&report);
    emit(report, text, json_mode)
}
