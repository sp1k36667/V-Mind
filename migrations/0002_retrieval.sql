-- Bestehende Einträge gehören zunächst zum gemeinsamen Bereich global.
ALTER TABLE memories ADD COLUMN scope TEXT NOT NULL DEFAULT 'global'
    CHECK (length(trim(scope)) > 0);
CREATE INDEX memories_scope_status ON memories(scope, status);

CREATE TABLE invalidations (
    memory_id INTEGER PRIMARY KEY REFERENCES memories(id),
    actor TEXT NOT NULL CHECK (length(trim(actor)) > 0),
    reason TEXT NOT NULL CHECK (length(trim(reason)) > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;
CREATE TABLE memory_events (
    id INTEGER PRIMARY KEY,
    memory_id INTEGER NOT NULL REFERENCES memories(id),
    action TEXT NOT NULL CHECK (action IN ('created', 'validated', 'invalidated', 'imported')),
    actor TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;
CREATE INDEX memory_events_memory ON memory_events(memory_id, id);
-- Keine historischen Zeitpunkte erfinden: Die Übernahme wird als Import dokumentiert.
INSERT INTO memory_events(memory_id, action, actor, reason)
    SELECT id, 'imported', 'migration-v2', 'Aus Schema 1 übernommen; ursprünglicher Status: ' || status
    FROM memories;
CREATE TRIGGER memory_created AFTER INSERT ON memories BEGIN
    INSERT INTO memory_events(memory_id, action, actor, reason)
    VALUES (new.id, 'created', new.source, 'Ungeprüften Eintrag gespeichert');
END;
CREATE TRIGGER memory_validated AFTER UPDATE OF status ON memories
WHEN old.status = 'pending' AND new.status = 'validated' BEGIN
    INSERT INTO memory_events(memory_id, action, actor, reason)
    VALUES (new.id, 'validated', new.validated_by, new.evidence);
END;
CREATE TRIGGER memory_invalidated AFTER INSERT ON invalidations BEGIN
    INSERT INTO memory_events(memory_id, action, actor, reason)
    VALUES (new.memory_id, 'invalidated', new.actor, new.reason);
END;

CREATE VIRTUAL TABLE memories_fts USING fts5(
    problem, solution, content='memories', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER memories_fts_insert AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, problem, solution) VALUES(new.id, new.problem, new.solution);
END;
CREATE TRIGGER memories_fts_delete AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, problem, solution)
        VALUES('delete', old.id, old.problem, old.solution);
END;
CREATE TRIGGER memories_fts_update AFTER UPDATE OF problem, solution ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, problem, solution)
        VALUES('delete', old.id, old.problem, old.solution);
    INSERT INTO memories_fts(rowid, problem, solution) VALUES(new.id, new.problem, new.solution);
END;
INSERT INTO memories_fts(memories_fts) VALUES('rebuild');
