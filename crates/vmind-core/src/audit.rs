//! Rein lesende Suche nach bekannten Geheimnisformaten in allen Textfeldern einer
//! Datenbank. Gibt nur Tabelle, Zeilennummer, Feld und Fundart aus, nie Feldwerte,
//! Textausschnitte oder Text-IDs. Keine Garantie: siehe `NOTICE`.
use crate::{
    SCHEMA_VERSION, invalid,
    secrets::{SecretKind, detect},
};
use rusqlite::{Connection, Result, types::ValueRef};
use serde::Serialize;
use std::{collections::BTreeSet, path::Path};

pub const NOTICE: &str = "Erkennt nur bekannte Formate; kein Fund heißt nicht geheimnisfrei. \
JWT und URL-Zugangsdaten sind unsicher (auch Beispiele sehen so aus). Prüfausgaben sind nur \
gekürzt gespeichert (letzte 4000 Zeichen), dort angeschnittene Geheimnisse werden nicht erkannt; \
kodierte Inhalte nur, soweit sie JSON sind. Nicht durchsucht: Suchindizes, freie Seiten und \
WAL der Datei, Sicherungen und andere Kopien.";

/// Welche Zeile ein Fund betrifft. Nur Zahlen, damit keine Text-ID ein Geheimnis ausgibt.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize)]
pub struct AuditFinding {
    pub table: &'static str,
    /// Primärschlüssel; bei `conversations` die SQLite-rowid, weil die ID Text ist.
    pub row_id: i64,
    pub field: &'static str,
    pub kind: SecretKind,
    pub label: &'static str,
    pub certain: bool,
    /// Betroffener Wissenseintrag, auch bei Historie, Rückzug und Prüfbefehlen.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub memory_id: Option<i64>,
    /// rowid des Gesprächs einer Nachricht.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub conversation_row: Option<i64>,
}

#[derive(Debug, Serialize)]
pub struct ScannedTable {
    pub table: &'static str,
    pub rows: i64,
    pub fields: Vec<&'static str>,
}

#[derive(Debug, Serialize)]
pub struct AuditReport {
    pub schema_version: i64,
    pub notice: &'static str,
    pub scanned: Vec<ScannedTable>,
    pub findings: Vec<AuditFinding>,
}

#[derive(Clone, Copy)]
enum Parent {
    None,
    Memory(&'static str),
    Conversation(&'static str),
}

struct Source {
    table: &'static str,
    min_schema: i64,
    id: &'static str,
    parent: Parent,
    fields: &'static [&'static str],
    /// Felder, die JSON enthalten können; deren Zeichenketten werden zusätzlich dekodiert geprüft.
    json: &'static [&'static str],
}

// Aufzählungsspalten mit CHECK (kind, status, role, tool …) und Zeitstempel fehlen bewusst.
const SOURCES: &[Source] = &[
    Source {
        table: "memories",
        min_schema: 1,
        id: "id",
        parent: Parent::Memory("id"),
        fields: &[
            "scope",
            "problem",
            "solution",
            "source",
            "validated_by",
            "evidence",
        ],
        json: &[],
    },
    Source {
        table: "memory_events",
        min_schema: 2,
        id: "id",
        parent: Parent::Memory("memory_id"),
        fields: &["actor", "reason"],
        json: &[],
    },
    Source {
        table: "invalidations",
        min_schema: 2,
        id: "memory_id",
        parent: Parent::Memory("memory_id"),
        fields: &["actor", "reason"],
        json: &[],
    },
    Source {
        table: "project_journal",
        min_schema: 3,
        id: "id",
        parent: Parent::None,
        fields: &["scope", "task_key", "body", "source"],
        json: &[],
    },
    Source {
        table: "conversations",
        min_schema: 3,
        id: "rowid",
        parent: Parent::None,
        fields: &["id", "scope", "title"],
        json: &[],
    },
    Source {
        table: "chat_messages",
        min_schema: 3,
        id: "id",
        parent: Parent::Conversation(
            "(SELECT c.rowid FROM conversations c WHERE c.id=chat_messages.conversation_id)",
        ),
        fields: &["content"],
        json: &["content"],
    },
    Source {
        table: "memory_checks",
        min_schema: 4,
        id: "id",
        parent: Parent::Memory("memory_id"),
        fields: &["argv", "workdir", "set_by"],
        json: &["argv"],
    },
    Source {
        table: "check_runs",
        min_schema: 4,
        id: "id",
        parent: Parent::Memory(
            "(SELECT c.memory_id FROM memory_checks c WHERE c.id=check_runs.check_id)",
        ),
        fields: &["output"],
        json: &[],
    },
    Source {
        table: "observations",
        min_schema: 6,
        id: "id",
        parent: Parent::None,
        fields: &["scope", "session_id", "tool_use_id", "paths"],
        json: &["paths"],
    },
];

fn table_exists(conn: &Connection, table: &str) -> Result<bool> {
    conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name=?1)",
        [table],
        |r| r.get(0),
    )
}

/// Nur Spalten, die es in diesem Schema gibt; ältere Datenbanken haben weniger.
fn present_fields(conn: &Connection, source: &Source) -> Result<Vec<&'static str>> {
    let columns = conn
        .prepare("SELECT name FROM pragma_table_info(?1)")?
        .query_map([source.table], |r| r.get::<_, String>(0))?
        .collect::<Result<BTreeSet<_>>>()?;
    Ok(source
        .fields
        .iter()
        .copied()
        .filter(|f| columns.contains(*f))
        .collect())
}

fn collect_strings(value: &serde_json::Value, out: &mut Vec<String>) {
    match value {
        serde_json::Value::String(s) => out.push(s.clone()),
        serde_json::Value::Array(items) => items.iter().for_each(|v| collect_strings(v, out)),
        serde_json::Value::Object(map) => map.iter().for_each(|(k, v)| {
            out.push(k.clone());
            collect_strings(v, out);
        }),
        _ => {}
    }
}

/// Fundarten des Rohtexts und, bei JSON-Feldern, jeder dekodierten Zeichenkette.
fn kinds(text: &str, json: bool) -> BTreeSet<SecretKind> {
    let mut found: BTreeSet<_> = detect(text).into_iter().collect();
    if json && let Ok(value) = serde_json::from_str::<serde_json::Value>(text) {
        let mut strings = Vec::new();
        collect_strings(&value, &mut strings);
        found.extend(strings.iter().flat_map(|s| detect(s)));
    }
    found
}

fn scan_source(
    conn: &Connection,
    source: &Source,
    fields: &[&'static str],
    findings: &mut Vec<AuditFinding>,
) -> Result<i64> {
    let parent = match source.parent {
        Parent::None => "NULL",
        Parent::Memory(expr) | Parent::Conversation(expr) => expr,
    };
    // Alle Bezeichner stammen aus den festen Listen oben, nie aus Eingaben.
    let sql = format!(
        "SELECT {}, {parent}, {} FROM {} ORDER BY 1",
        source.id,
        fields.join(", "),
        source.table
    );
    let mut stmt = conn.prepare(&sql)?;
    let mut rows = stmt.query([])?;
    let mut count = 0;
    while let Some(row) = rows.next()? {
        count += 1;
        let row_id: i64 = row.get(0)?;
        let parent_id: Option<i64> = row.get(1)?;
        for (i, &field) in fields.iter().enumerate() {
            let text = match row.get_ref(i + 2)? {
                ValueRef::Text(bytes) => String::from_utf8_lossy(bytes),
                _ => continue,
            };
            for kind in kinds(&text, source.json.contains(&field)) {
                findings.push(AuditFinding {
                    table: source.table,
                    row_id,
                    field,
                    kind,
                    label: kind.label(),
                    certain: kind.certain(),
                    memory_id: matches!(source.parent, Parent::Memory(_))
                        .then_some(parent_id)
                        .flatten(),
                    conversation_row: matches!(source.parent, Parent::Conversation(_))
                        .then_some(parent_id)
                        .flatten(),
                });
            }
        }
    }
    Ok(count)
}

/// Durchsucht eine vorhandene Datenbank in einem Snapshot. Öffnet nur lesend, legt
/// nichts an und stellt kein Schema um; ältere Schemas werden mit ihren Tabellen geprüft.
pub fn audit_secrets(path: impl AsRef<Path>) -> Result<AuditReport> {
    let conn = crate::maintenance::read_only(path.as_ref())?;
    let tx = conn.unchecked_transaction()?;
    let version: i64 = tx.query_row("PRAGMA user_version", [], |r| r.get(0))?;
    if !(1..=SCHEMA_VERSION).contains(&version) {
        return Err(invalid(
            "Keine V-Mind-Datenbank mit bekanntem Schema; nichts durchsucht",
        ));
    }
    let mut scanned = Vec::new();
    let mut findings = Vec::new();
    for source in SOURCES {
        if !table_exists(&tx, source.table)? {
            if version >= source.min_schema {
                return Err(invalid(
                    "Erforderliche Audit-Tabelle fehlt; keine vollständige Prüfung",
                ));
            }
            continue;
        }
        let fields = present_fields(&tx, source)?;
        let expected = source
            .fields
            .iter()
            .filter(|&&field| !(version == 1 && source.table == "memories" && field == "scope"))
            .count();
        if fields.len() != expected {
            return Err(invalid(
                "Erforderliches Audit-Feld fehlt; keine vollständige Prüfung",
            ));
        }
        let rows = scan_source(&tx, source, &fields, &mut findings)?;
        scanned.push(ScannedTable {
            table: source.table,
            rows,
            fields,
        });
    }
    tx.commit()?;
    findings.sort();
    Ok(AuditReport {
        schema_version: version,
        notice: NOTICE,
        scanned,
        findings,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{MemoryStore, Observation, secrets::samples};
    use std::{fs, path::PathBuf};

    fn temp_db(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "vmind-audit-{name}-{}-{:?}",
            std::process::id(),
            std::thread::current().id()
        ));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir.join("vmind.db")
    }

    /// Legt `marker` in jedem Speicherweg ab und liefert die erwarteten (Tabelle, Feld).
    fn fill(store: &MemoryStore, marker: &str) -> Vec<(&'static str, &'static str)> {
        let id = store
            .remember_scoped("p", "error_solution", marker, "Lösung", "Quelle")
            .unwrap();
        store
            .remember_scoped("p", "error_solution", "Problem", marker, "Quelle")
            .unwrap();
        let src = store
            .remember_scoped("p", "error_solution", "Problem", "Lösung", marker)
            .unwrap();
        store.validate(src, marker, "Nachweis").unwrap();
        let ev = store
            .remember_scoped("p", "error_solution", "Problem", "Lösung", "Quelle")
            .unwrap();
        store.validate(ev, "Prüfer", marker).unwrap();
        store.invalidate(id, marker, marker).unwrap();
        store
            .journal("p", "task", Some(marker), Some("open"), "Text", "Quelle")
            .unwrap();
        store
            .journal("p", "note", None, None, marker, marker)
            .unwrap();
        let conv = store.create_conversation("p", marker).unwrap();
        // Erstes Zeichen als JSON-Escape, damit nur die Dekodierung den Wert findet.
        let escaped = format!("\\u{:04x}{}", marker.as_bytes()[0], &marker[1..]);
        assert!(detect(&escaped).is_empty());
        store
            .append_message(&conv, "tool", &format!("{{\"text\": \"{escaped}\"}}"))
            .unwrap();
        let checked = store
            .remember_scoped("p", "error_solution", "Problem", "Lösung", "Quelle")
            .unwrap();
        let check = store
            .set_check(checked, &["echo".into(), marker.into()], marker, marker)
            .unwrap();
        store
            .conn
            .execute(
                "INSERT INTO check_runs(check_id,outcome,exit_code,duration_ms,output)
                VALUES(?1,'failed',1,1,?2)",
                rusqlite::params![check, format!("Ausgabe {marker}")],
            )
            .unwrap();
        store
            .observe(
                "p",
                &Observation {
                    session_id: marker.into(),
                    tool_use_id: marker.into(),
                    tool: "Edit".into(),
                    result: "completed".into(),
                    paths: vec![format!("src/{marker}.rs")],
                },
            )
            .unwrap();
        vec![
            ("memories", "problem"),
            ("memories", "solution"),
            ("memories", "source"),
            ("memories", "validated_by"),
            ("memories", "evidence"),
            ("memory_events", "actor"),
            ("memory_events", "reason"),
            ("invalidations", "actor"),
            ("invalidations", "reason"),
            ("project_journal", "task_key"),
            ("project_journal", "body"),
            ("project_journal", "source"),
            ("conversations", "title"),
            ("chat_messages", "content"),
            ("memory_checks", "argv"),
            ("memory_checks", "workdir"),
            ("memory_checks", "set_by"),
            ("check_runs", "output"),
            ("observations", "session_id"),
            ("observations", "tool_use_id"),
            ("observations", "paths"),
        ]
    }

    #[test]
    fn finds_marker_in_every_storage_path_without_revealing_it_or_changing_the_file() {
        let (kind, marker) = samples::all()
            .into_iter()
            .find(|(k, _)| *k == SecretKind::GithubToken)
            .unwrap();
        let path = temp_db("all");
        let expected = {
            let store = MemoryStore::open_file(&path).unwrap();
            fill(&store, &marker)
        };
        let before = fs::read(&path).unwrap();

        let report = audit_secrets(&path).unwrap();

        assert_eq!(fs::read(&path).unwrap(), before, "Datei verändert");
        let found: BTreeSet<_> = report
            .findings
            .iter()
            .filter(|f| f.kind == kind)
            .map(|f| (f.table, f.field))
            .collect();
        for place in &expected {
            assert!(found.contains(place), "nicht gefunden: {place:?}");
        }
        let json = serde_json::to_string(&report).unwrap();
        assert!(!json.contains(&marker), "Fundtext in der Ausgabe");
        assert!(!json.contains(&marker[4..20]), "Teilstring in der Ausgabe");
        let run = report
            .findings
            .iter()
            .find(|f| f.table == "check_runs")
            .unwrap();
        assert!(run.memory_id.is_some(), "Prüflauf ohne Eintragsbezug");
        let msg = report
            .findings
            .iter()
            .find(|f| f.table == "chat_messages")
            .unwrap();
        assert!(msg.conversation_row.is_some());
    }

    #[test]
    fn every_synthetic_kind_is_found_in_a_stored_entry() {
        let path = temp_db("kinds");
        let store = MemoryStore::open_file(&path).unwrap();
        for (_, value) in samples::all() {
            store
                .remember_scoped("p", "long_term", "Problem", &value, "Quelle")
                .unwrap();
        }
        drop(store);
        let kinds: BTreeSet<_> = audit_secrets(&path)
            .unwrap()
            .findings
            .iter()
            .map(|f| f.kind)
            .collect();
        let expected: BTreeSet<_> = samples::all().into_iter().map(|(k, _)| k).collect();
        assert_eq!(kinds, expected);
    }

    #[test]
    fn ordinary_database_has_no_findings_and_lists_scanned_tables() {
        let path = temp_db("clean");
        let store = MemoryStore::open_file(&path).unwrap();
        store
            .remember_scoped(
                "p",
                "error_solution",
                "Token abgelaufen",
                "Neu anmelden",
                "Test",
            )
            .unwrap();
        store
            .journal("p", "note", None, None, "Notiz", "Test")
            .unwrap();
        drop(store);
        let report = audit_secrets(&path).unwrap();
        assert!(report.findings.is_empty());
        assert_eq!(report.schema_version, SCHEMA_VERSION);
        let tables: Vec<_> = report.scanned.iter().map(|t| t.table).collect();
        assert_eq!(tables.len(), SOURCES.len());
        assert!(
            report
                .notice
                .contains("kein Fund heißt nicht geheimnisfrei")
        );
    }

    #[test]
    fn missing_file_is_an_error_and_is_not_created() {
        let path = temp_db("missing");
        fs::remove_file(&path).ok();
        assert!(audit_secrets(&path).is_err());
        assert!(!path.exists());
    }

    #[test]
    fn foreign_or_unknown_schema_is_refused() {
        let path = temp_db("foreign");
        let conn = Connection::open(&path).unwrap();
        conn.execute_batch("CREATE TABLE t(x TEXT);").unwrap();
        drop(conn);
        assert!(audit_secrets(&path).is_err());
        let conn = Connection::open(&path).unwrap();
        conn.pragma_update(None, "user_version", SCHEMA_VERSION + 1)
            .unwrap();
        drop(conn);
        assert!(audit_secrets(&path).is_err());
    }

    #[test]
    fn known_version_without_required_tables_is_not_a_clean_audit() {
        let path = temp_db("empty-known");
        let conn = Connection::open(&path).unwrap();
        conn.pragma_update(None, "user_version", 5).unwrap();
        drop(conn);
        assert!(audit_secrets(&path).is_err());
    }

    #[test]
    fn missing_required_table_or_text_column_is_not_silently_skipped() {
        let path = temp_db("missing-fields");
        drop(MemoryStore::open_file(&path).unwrap());
        let conn = Connection::open(&path).unwrap();
        conn.execute_batch("ALTER TABLE memories RENAME COLUMN solution TO hidden_solution;")
            .unwrap();
        assert!(audit_secrets(&path).is_err());
        conn.execute_batch("ALTER TABLE memories RENAME COLUMN hidden_solution TO solution; DROP TABLE observations;").unwrap();
        assert!(audit_secrets(&path).is_err());
    }

    #[test]
    fn older_schema_is_scanned_without_upgrade() {
        let path = temp_db("old");
        let conn = Connection::open(&path).unwrap();
        conn.execute_batch(include_str!("../../../migrations/0001_memory.sql"))
            .unwrap();
        conn.pragma_update(None, "user_version", 1).unwrap();
        let marker = &samples::all()[1].1;
        conn.execute(
            "INSERT INTO memories(kind,problem,solution,source) VALUES('long_term',?1,'L','Q')",
            [marker],
        )
        .unwrap();
        drop(conn);
        let report = audit_secrets(&path).unwrap();
        assert_eq!(report.schema_version, 1);
        assert_eq!(report.findings.len(), 1);
        assert_eq!(report.findings[0].field, "problem");
        let conn = Connection::open(&path).unwrap();
        let version: i64 = conn
            .query_row("PRAGMA user_version", [], |r| r.get(0))
            .unwrap();
        assert_eq!(version, 1, "Schema wurde umgestellt");
    }
}
