//! File APIs must never silently reinterpret filenames as SQLite URI options.
use crate::invalid;
use rusqlite::Result;
use std::path::{Path, PathBuf};

pub fn literal_file_path(path: impl AsRef<Path>) -> Result<PathBuf> {
    let path = path.as_ref();
    let name = path.as_os_str().as_encoded_bytes();
    if name.is_empty() {
        return Err(invalid("Datenbank-Dateipfad darf nicht leer sein"));
    }
    if name.starts_with(b"file:") || name == b":memory:" {
        // Preserve the literal spelling for both filesystem and SQLite. No URI
        // options or verbatim Windows canonical paths are introduced.
        Ok(Path::new(".").join(path))
    } else {
        Ok(path.to_path_buf())
    }
}
