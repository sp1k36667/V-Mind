-- Herkunft des Gesprächsverlaufs: Werkzeug und, wenn belegt, Modell je Nachricht. SQLite kann
-- UNIQUE-Bedingungen nicht ändern, daher werden beide Tabellen neu aufgebaut. Die IDs bleiben
-- erhalten, damit der externe Volltextindex weiter passt; Bestandszeilen werden `claude-code`.
DROP TRIGGER history_fts_insert;
DROP TRIGGER history_fts_delete;
DROP TRIGGER history_fts_update;

CREATE TABLE history_messages_new (
    id INTEGER PRIMARY KEY,
    scope TEXT NOT NULL CHECK(length(trim(scope))>0 AND length(scope)<=128),
    tool TEXT NOT NULL CHECK(tool IN ('claude-code','codex')),
    model TEXT CHECK(model IS NULL OR (length(trim(model))>0 AND length(model)<=200)),
    session_id TEXT NOT NULL CHECK(length(trim(session_id))>0 AND length(session_id)<=200),
    uuid TEXT NOT NULL CHECK(length(trim(uuid))>0 AND length(uuid)<=200),
    role TEXT NOT NULL CHECK(role IN ('user','assistant')),
    text TEXT NOT NULL CHECK(length(trim(text))>0),
    created_at TEXT NOT NULL CHECK(length(trim(created_at))>0 AND length(created_at)<=64),
    UNIQUE(scope, tool, uuid)
) STRICT;
INSERT INTO history_messages_new(id, scope, tool, model, session_id, uuid, role, text, created_at)
    SELECT id, scope, 'claude-code', NULL, session_id, uuid, role, text, created_at
    FROM history_messages;
DROP TABLE history_messages;
ALTER TABLE history_messages_new RENAME TO history_messages;

CREATE TRIGGER history_fts_insert AFTER INSERT ON history_messages BEGIN
    INSERT INTO history_fts(rowid, text) VALUES(new.id, new.text);
END;
CREATE TRIGGER history_fts_delete AFTER DELETE ON history_messages BEGIN
    INSERT INTO history_fts(history_fts, rowid, text) VALUES('delete', old.id, old.text);
END;
CREATE TRIGGER history_fts_update AFTER UPDATE OF text ON history_messages BEGIN
    INSERT INTO history_fts(history_fts, rowid, text) VALUES('delete', old.id, old.text);
    INSERT INTO history_fts(rowid, text) VALUES(new.id, new.text);
END;

-- Importstand je Bereich, Werkzeug und Quelldatei. session_id und der letzte belegte Turn
-- erlauben einem Lauf ab Byte-Stand die Zuordnung ohne erneutes Lesen; last_error behält
-- sein Format, Warnungen bleiben also erhalten.
CREATE TABLE history_imports_new (
    id INTEGER PRIMARY KEY,
    scope TEXT NOT NULL CHECK(length(trim(scope))>0 AND length(scope)<=128),
    tool TEXT NOT NULL CHECK(tool IN ('claude-code','codex')),
    source_path TEXT NOT NULL CHECK(length(trim(source_path))>0 AND length(source_path)<=4096),
    byte_offset INTEGER NOT NULL DEFAULT 0 CHECK(byte_offset>=0),
    last_error TEXT,
    unkeyed_lines INTEGER NOT NULL DEFAULT 0 CHECK(unkeyed_lines>=0),
    session_id TEXT CHECK(session_id IS NULL OR length(session_id)<=200),
    last_turn_id TEXT CHECK(last_turn_id IS NULL OR length(last_turn_id)<=200),
    last_model TEXT CHECK(last_model IS NULL OR length(last_model)<=200),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE(scope, tool, source_path)
) STRICT;
INSERT INTO history_imports_new(id, scope, tool, source_path, byte_offset, last_error, updated_at)
    SELECT id, scope, 'claude-code', source_path, byte_offset, last_error, updated_at
    FROM history_imports;
DROP TABLE history_imports;
ALTER TABLE history_imports_new RENAME TO history_imports;
