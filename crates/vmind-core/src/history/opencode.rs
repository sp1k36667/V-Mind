//! Liest einen eigenständigen SQLite-Snapshot von OpenCode (`opencode.db`). Auch dieses Format
//! ist keine offizielle Schnittstelle. Die Quelle wird nur über `mode=ro&immutable=1`
//! geöffnet: SQLite legt dann weder `-wal` noch `-shm` an und ändert nichts. Ein Snapshot
//! mit nicht leerer `-wal`- oder einer `-journal`-Datei wird vorher abgelehnt, weil
//! `immutable` deren Inhalt nicht sähe.
//!
//! Übernommen werden nur Textteile (`type = text`) von Nutzer- und Assistentennachrichten
//! einer Wurzelsitzung. Teile mit `synthetic` oder `ignored`, alle anderen Teiltypen
//! (Reasoning, Werkzeuge, Dateien, Snapshots, Schritte, Kompaktierung …), der Systemtext
//! `system`, Kompaktierungszusammenfassungen (`summary`), unfertige Assistentennachrichten und
//! Kindsitzungen (`parent_id`, etwa Unteragenten) entfallen.
use super::{MAX_ID_CHARS, Message, bounded_id, stored_text, watch_scan::iso_from_millis};
use rusqlite::{Connection, OpenFlags, params, types::ValueRef};
use serde_json::Value;
use std::{
    collections::{HashMap, HashSet},
    fs,
    path::{Path, PathBuf},
};

/// Je Tabelle die gelesenen Spalten; weitere Spalten sind erlaubt.
const REQUIRED: [(&str, &[&str]); 3] = [
    ("session", &["id", "parent_id"]),
    ("message", &["id", "session_id", "time_created", "data"]),
    ("part", &["id", "message_id", "session_id", "data"]),
];
const SNAPSHOT_HINT: &str =
    "bitte konsistenten eigenständigen Snapshot übergeben (z. B. sqlite3 .backup)";

type Outcome<T> = std::result::Result<T, String>;

const URI_QUERY: &str = "?mode=ro&immutable=1";

/// `file:`-URI mit Prozentkodierung; nur nicht reservierte Zeichen, `/` und `:` bleiben, also
/// auch `%`, `?`, `#` und Leerzeichen werden kodiert.
fn encoded_uri(path: &[u8]) -> String {
    let mut uri = String::from("file:");
    for &byte in path {
        if byte.is_ascii_alphanumeric() || b"-._~/:".contains(&byte) {
            uri.push(char::from(byte));
        } else {
            uri.push_str(&format!("%{byte:02X}"));
        }
    }
    uri.push_str(URI_QUERY);
    uri
}

/// URI aus einem (kanonischen) Windows-Pfad als reine Zeichenkettenfunktion, damit sie auf
/// allen Plattformen testbar ist: `\\?\C:\a b` → `file:/C:/a%20b?…`,
/// `\\?\UNC\server\freigabe\x` → `file:////server/freigabe/x?…` (leere Autorität).
#[cfg_attr(not(windows), allow(dead_code))]
fn windows_uri(path: &str) -> String {
    let slashed = path.replace('\\', "/");
    let plain = if let Some(unc) = slashed.strip_prefix("//?/UNC/") {
        format!("////{unc}")
    } else if let Some(local) = slashed.strip_prefix("//?/") {
        format!("/{local}")
    } else if slashed.starts_with("//") {
        format!("//{slashed}")
    } else if slashed.starts_with('/') {
        slashed
    } else {
        format!("/{slashed}")
    };
    encoded_uri(plain.as_bytes())
}

fn uri_path(path: &Path) -> Outcome<String> {
    #[cfg(unix)]
    {
        use std::os::unix::ffi::OsStrExt;
        Ok(encoded_uri(path.as_os_str().as_bytes()))
    }
    #[cfg(windows)]
    {
        let text = path.to_str().ok_or("Quellpfad ist kein gültiges UTF-8")?;
        Ok(windows_uri(text))
    }
    #[cfg(not(any(unix, windows)))]
    {
        let text = path.to_str().ok_or("Quellpfad ist kein gültiges UTF-8")?;
        Ok(encoded_uri(text.as_bytes()))
    }
}

fn sidecar(path: &Path, suffix: &str) -> PathBuf {
    let mut name = path.as_os_str().to_owned();
    name.push(suffix);
    PathBuf::from(name)
}

/// Lehnt einen Snapshot mit aktiver WAL- oder Journaldatei ab, am angegebenen und am
/// aufgelösten Pfad.
fn reject_sidecars(paths: &[&Path]) -> Outcome<()> {
    for path in paths {
        let wal = sidecar(path, "-wal");
        if fs::symlink_metadata(&wal).is_ok_and(|m| m.len() > 0) {
            return Err(format!(
                "Aktive WAL-Datei neben der Quelle; {SNAPSHOT_HINT}"
            ));
        }
        if fs::symlink_metadata(sidecar(path, "-journal")).is_ok() {
            return Err(format!(
                "Aktive Journal-Datei neben der Quelle; {SNAPSHOT_HINT}"
            ));
        }
    }
    Ok(())
}

#[cfg(unix)]
fn same_inode(a: &fs::Metadata, b: &fs::Metadata) -> bool {
    use std::os::unix::fs::MetadataExt;
    a.dev() == b.dev() && a.ino() == b.ino()
}

/// Bekannte Grenze: Ohne instabile API gibt es auf anderen Systemen keine Dateikennung; ein
/// harter Link auf die V-Mind-Datenbank wird dort nicht als dieselbe Datei erkannt.
#[cfg(not(unix))]
fn same_inode(_: &fs::Metadata, _: &fs::Metadata) -> bool {
    false
}

/// Gleiche kanonische Pfade; unter Windows ohne Unterschied der Groß-/Kleinschreibung.
fn same_canonical(a: &Path, b: &Path) -> bool {
    if cfg!(windows) {
        a.to_string_lossy().to_lowercase() == b.to_string_lossy().to_lowercase()
    } else {
        a == b
    }
}

/// Ob der Snapshot dieselbe Datei wie die V-Mind-Datenbank ist: gleicher kanonischer Pfad
/// (auch über symbolische Links) oder unter Unix gleicher Inode (harter Link). Liest nur
/// Metadaten, öffnet keine der beiden Dateien.
pub(super) fn is_same_file(snapshot: &Path, target: &Path) -> bool {
    let (Ok(source), Ok(target_path)) = (fs::canonicalize(snapshot), fs::canonicalize(target))
    else {
        return false;
    };
    if same_canonical(&source, &target_path) {
        return true;
    }
    matches!(
        (fs::metadata(&source), fs::metadata(&target_path)),
        (Ok(a), Ok(b)) if same_inode(&a, &b)
    )
}

/// Kanonischer Pfad der Quelle nach allen Vorprüfungen.
fn checked_source(snapshot: &Path) -> Outcome<PathBuf> {
    let not_readable = |e: std::io::Error| format!("Quelle nicht lesbar: {}", e.kind());
    let canonical = fs::canonicalize(snapshot).map_err(not_readable)?;
    // Vor dem Öffnen prüfen: Eine FIFO würde blockieren.
    let meta = fs::metadata(&canonical).map_err(not_readable)?;
    if !meta.is_file() {
        return Err("Quelle ist keine reguläre Datei".into());
    }
    reject_sidecars(&[snapshot, &canonical])?;
    Ok(canonical)
}

fn check_schema(conn: &Connection) -> Outcome<()> {
    let failed = |_| "Schema der Quelle nicht lesbar".to_owned();
    for (table, columns) in REQUIRED {
        let mut stmt = conn
            .prepare("SELECT name FROM pragma_table_info(?1)")
            .map_err(failed)?;
        let present = stmt
            .query_map([table], |r| r.get::<_, String>(0))
            .and_then(|rows| rows.collect::<rusqlite::Result<HashSet<_>>>())
            .map_err(failed)?;
        if present.is_empty() {
            return Err(format!(
                "Unbekannte Struktur: Tabelle {table} fehlt; nichts übernommen"
            ));
        }
        if let Some(missing) = columns.iter().find(|c| !present.contains(**c)) {
            return Err(format!(
                "Unbekannte Struktur: Spalte {table}.{missing} fehlt; nichts übernommen"
            ));
        }
    }
    Ok(())
}

fn text_column(row: &rusqlite::Row<'_>, index: usize, what: &str) -> Outcome<String> {
    match row.get_ref(index) {
        Ok(ValueRef::Text(text)) => std::str::from_utf8(text)
            .map(str::to_owned)
            .map_err(|_| format!("{what} ist kein gültiges UTF-8")),
        _ => Err(format!("{what} ist kein Text")),
    }
}

fn checked_id(value: String, what: &str) -> Outcome<String> {
    if bounded_id(&value, MAX_ID_CHARS) {
        Ok(value)
    } else {
        Err(format!("{what} ist ungültig"))
    }
}

fn json_object(raw: &str, what: &str) -> Outcome<Value> {
    match serde_json::from_str::<Value>(raw) {
        Ok(value) if value.is_object() => Ok(value),
        _ => Err(format!(
            "Unbekannte Struktur: data von {what} ist kein JSON-Objekt"
        )),
    }
}

/// Ein fehlendes Kennzeichen gilt als `false`; ein anderer Typ ist eine unbekannte Struktur.
fn flag(data: &Value, key: &str, what: &str) -> Outcome<bool> {
    match data.get(key) {
        None | Some(Value::Null) => Ok(false),
        Some(Value::Bool(value)) => Ok(*value),
        Some(_) => Err(format!(
            "Unbekannte Struktur: {key} von {what} ist kein Wahrheitswert"
        )),
    }
}

/// Übernehmbarer Inhalt der Teile einer Nachricht.
#[derive(Default)]
struct Parts {
    texts: Vec<String>,
    compaction: bool,
}

/// Teile je (Sitzung, Nachricht): Ein Teil gehört nur zu einer Nachricht, wenn Sitzung und
/// Nachrichten-ID beide übereinstimmen.
type PartsByMessage = HashMap<(String, String), Parts>;

fn read_parts(conn: &Connection, session: Option<&str>) -> Outcome<PartsByMessage> {
    let failed = |_| "Teile der Quelle nicht lesbar".to_owned();
    let mut stmt = conn
        .prepare(
            "SELECT id, session_id, message_id, data FROM part
             WHERE ?1 IS NULL OR session_id=?1 ORDER BY session_id, message_id, id",
        )
        .map_err(failed)?;
    let mut rows = stmt.query(params![session]).map_err(failed)?;
    let mut parts = PartsByMessage::new();
    while let Some(row) = rows.next().map_err(failed)? {
        let id = checked_id(text_column(row, 0, "Teil-ID")?, "Teil-ID")?;
        let what = format!("Teil {id}");
        let part_session = checked_id(text_column(row, 1, &what)?, &what)?;
        let message = checked_id(text_column(row, 2, &what)?, &what)?;
        let data = json_object(&text_column(row, 3, &what)?, &what)?;
        let entry = parts.entry((part_session, message)).or_default();
        match data["type"].as_str() {
            None => return Err(format!("Unbekannte Struktur: {what} ohne Typ")),
            Some("text") => {
                let skipped = flag(&data, "synthetic", &what)? | flag(&data, "ignored", &what)?;
                let text = data["text"]
                    .as_str()
                    .ok_or_else(|| format!("Unbekannte Struktur: {what} ohne Text"))?;
                if !skipped {
                    entry.texts.push(text.to_owned());
                }
            }
            Some("compaction") => entry.compaction = true,
            // Reasoning, Werkzeuge, Dateien, Schritte, Snapshots und Unbekanntes entfallen.
            Some(_) => {}
        }
    }
    Ok(parts)
}

/// `anbieter/modell`, nur wenn beide Angaben gültig vorliegen.
fn model_of(provider: &Value, model: &Value) -> Option<String> {
    let (provider, model) = (provider.as_str()?, model.as_str()?);
    let joined = format!("{provider}/{model}");
    (bounded_id(provider, MAX_ID_CHARS) && bounded_id(model, MAX_ID_CHARS))
        .then_some(joined)
        .filter(|m| bounded_id(m, MAX_ID_CHARS))
}

/// Rolle und Modell, oder `None` für eine Nachricht, die nicht übernommen wird.
fn message_kind(data: &Value, what: &str) -> Outcome<Option<(&'static str, Option<String>)>> {
    match data["role"].as_str() {
        Some("user") => Ok(Some((
            "user",
            model_of(&data["model"]["providerID"], &data["model"]["modelID"]),
        ))),
        Some("assistant") => {
            // Kompaktierungszusammenfassung oder noch nicht abgeschlossene Antwort.
            if flag(data, "summary", what)? || !data["time"]["completed"].is_number() {
                return Ok(None);
            }
            Ok(Some((
                "assistant",
                model_of(&data["providerID"], &data["modelID"]),
            )))
        }
        _ => Err(format!("Unbekannte Struktur: Rolle von {what} unbekannt")),
    }
}

fn read_messages(
    conn: &Connection,
    session: Option<&str>,
    mut parts: PartsByMessage,
) -> Outcome<Vec<Message>> {
    let failed = |_| "Nachrichten der Quelle nicht lesbar".to_owned();
    let mut stmt = conn
        .prepare(
            "SELECT m.id, m.session_id, m.time_created, m.data
             FROM message m JOIN session s ON s.id=m.session_id
             WHERE s.parent_id IS NULL AND (?1 IS NULL OR m.session_id=?1)
             ORDER BY m.time_created, m.id",
        )
        .map_err(failed)?;
    let mut rows = stmt.query(params![session]).map_err(failed)?;
    let mut messages = Vec::new();
    while let Some(row) = rows.next().map_err(failed)? {
        let id = checked_id(text_column(row, 0, "Nachrichten-ID")?, "Nachrichten-ID")?;
        let what = format!("Nachricht {id}");
        let session_id = checked_id(text_column(row, 1, &what)?, &what)?;
        let created_at = match row.get_ref(2) {
            Ok(ValueRef::Integer(millis)) => iso_from_millis(millis),
            _ => None,
        }
        .ok_or_else(|| format!("Unbekannte Struktur: time_created von {what} ungültig"))?;
        let data = json_object(&text_column(row, 3, &what)?, &what)?;
        let Some((role, model)) = message_kind(&data, &what)? else {
            continue;
        };
        let Some(found) = parts.remove(&(session_id.clone(), id.clone())) else {
            continue;
        };
        if found.compaction {
            continue;
        }
        let text = found.texts.join("\n");
        if text.trim().is_empty() {
            continue;
        }
        let uuid = format!("opencode:{session_id}:{id}");
        if !bounded_id(&uuid, MAX_ID_CHARS) {
            return Err(format!("Schlüssel von {what} zu lang"));
        }
        messages.push(Message {
            session_id,
            uuid,
            role,
            text: stored_text(&text),
            created_at,
            model,
            turn_id: None,
        });
    }
    Ok(messages)
}

/// Liest alle übernehmbaren Nachrichten oder liefert eine Meldung ohne Inhalte der Quelle.
pub(super) fn read_snapshot(snapshot: &Path, session: Option<&str>) -> Outcome<Vec<Message>> {
    let canonical = checked_source(snapshot)?;
    let conn = Connection::open_with_flags(
        uri_path(&canonical)?,
        OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_URI,
    )
    .map_err(|_| "Quelle lässt sich nicht als SQLite-Datenbank öffnen".to_owned())?;
    check_schema(&conn)?;
    let parts = read_parts(&conn, session)?;
    read_messages(&conn, session, parts)
}

#[cfg(test)]
mod tests {
    use super::{encoded_uri, windows_uri};

    const Q: &str = "?mode=ro&immutable=1";

    #[test]
    fn uri_encodes_reserved_characters() {
        assert_eq!(
            encoded_uri(b"/a b/c%d?e#f:g.db"),
            format!("file:/a%20b/c%25d%3Fe%23f:g.db{Q}")
        );
    }

    #[test]
    fn windows_paths_become_valid_uris() {
        let cases = [
            (
                r"\\?\C:\Daten\a b\snap%1#.db",
                "file:/C:/Daten/a%20b/snap%251%23.db",
            ),
            (r"C:\x\y.db", "file:/C:/x/y.db"),
            (
                r"\\?\UNC\server\freigabe\o.db",
                "file:////server/freigabe/o.db",
            ),
            (r"\\server\freigabe\o.db", "file:////server/freigabe/o.db"),
            (r"\\?\D:\ä.db", "file:/D:/%C3%A4.db"),
        ];
        for (path, uri) in cases {
            assert_eq!(windows_uri(path), format!("{uri}{Q}"), "{path}");
        }
    }
}
