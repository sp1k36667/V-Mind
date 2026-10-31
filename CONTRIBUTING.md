# Beiträge zu V-Mind

V-Mind ist ein früher Rust-/SQLite-Prototyp. Der dauerhafte Speicherkern bleibt
unabhängig von Sprachmodellen, Ollama und GPU-Treibern. Änderungen sollen Quellen,
Prüfnachweise, Projekttrennung und den Ausschluss zurückgezogener Einträge erhalten.

## Lokal prüfen

Voraussetzungen: Rust/Cargo (lokal geprüft mit 1.95.0), Git, pkg-config und SQLite
mit FTS5 samt Entwicklungsbibliothek. Jeder Befehl wird einzeln ausgeführt.

```sh
cargo fmt --all -- --check
```

```sh
cargo clippy --workspace --all-targets --locked -- -D warnings
```

```sh
cargo test --workspace --locked
```

Die Rust-Tests benötigen weder ein Modell noch eine GPU. Experimentelle Gemma-
Beispiele benötigen zusätzlich Python und eine passende lokale Ollama-Installation.

## Daten und Migrationen

Keine Datenbanken, Gesprächsverläufe, Zugangsdaten, Backups oder lokalen Modellgewichte
committen. Neue Schemaänderungen erhalten eine neue nummerierte Migration; bestehende
Migrationen nicht nachträglich ändern. Vor Änderungen einer Nutzerdatenbank ein
geprüftes SQLite-Backup anlegen.

## Aussagekräftige Änderungen

Problem, geändertes Verhalten und tatsächlich ausgeführte Prüfungen beschreiben.
Wissensvorschläge bleiben ungeprüft, bis eine passende externe Prüfung dokumentiert
wurde. Lokale Einzeltests nicht als Beweis für allgemeines Modelllernen darstellen.
