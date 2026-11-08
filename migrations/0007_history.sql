-- Automatisch übernommener Gesprächsverlauf einer KI: nur Text von Nutzer- und
-- Assistentennachrichten, bekannte Geheimnisformate vorab redigiert. Bewusst getrennt vom
-- Wissen und vom Projekttagebuch; Verlauf ist kein Prüfnachweis.
CREATE TABLE history_messages (
    id INTEGER PRIMARY KEY,
    scope TEXT NOT NULL CHECK(length(trim(scope))>0 AND length(scope)<=128),
    session_id TEXT NOT NULL CHECK(length(trim(session_id))>0 AND length(session_id)<=200),
    uuid TEXT NOT NULL CHECK(length(trim(uuid))>0 AND length(uuid)<=200),
    role TEXT NOT NULL CHECK(role IN ('user','assistant')),
    text TEXT NOT NULL CHECK(length(trim(text))>0),
    created_at TEXT NOT NULL CHECK(length(trim(created_at))>0 AND length(created_at)<=64),
    UNIQUE(scope, uuid)
) STRICT;

CREATE VIRTUAL TABLE history_fts USING fts5(
    text, content='history_messages', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
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

-- Importstand je Bereich und Quelldatei. byte_offset zeigt hinter die letzte vollständig
-- übernommene Zeile; last_error enthält nie Zeileninhalte.
CREATE TABLE history_imports (
    id INTEGER PRIMARY KEY,
    scope TEXT NOT NULL CHECK(length(trim(scope))>0 AND length(scope)<=128),
    source_path TEXT NOT NULL CHECK(length(trim(source_path))>0 AND length(source_path)<=4096),
    byte_offset INTEGER NOT NULL DEFAULT 0 CHECK(byte_offset>=0),
    last_error TEXT,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE(scope, source_path)
) STRICT;
