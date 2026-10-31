-- Ausführbare Prüfungen: Befehl ohne Shell (argv als JSON-Liste) im festen Arbeitsordner.
-- Mehrere Zeilen pro Eintrag sind möglich; die neueste ist aktiv, ältere bleiben Historie.
CREATE TABLE memory_checks (
    id INTEGER PRIMARY KEY,
    memory_id INTEGER NOT NULL REFERENCES memories(id),
    argv TEXT NOT NULL CHECK (
        json_valid(argv) AND json_type(argv) = 'array' AND json_array_length(argv) > 0
    ),
    workdir TEXT NOT NULL CHECK (length(trim(workdir)) > 0),
    set_by TEXT NOT NULL CHECK (length(trim(set_by)) > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;
CREATE INDEX memory_checks_memory ON memory_checks(memory_id, id);

-- Jeder Lauf wird festgehalten. "error" bedeutet: Befehl nicht startbar oder Zeitlimit,
-- also keine Aussage über den Eintrag.
CREATE TABLE check_runs (
    id INTEGER PRIMARY KEY,
    check_id INTEGER NOT NULL REFERENCES memory_checks(id),
    outcome TEXT NOT NULL CHECK (outcome IN ('passed', 'failed', 'error')),
    exit_code INTEGER,
    duration_ms INTEGER NOT NULL CHECK (duration_ms >= 0),
    output TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;
CREATE INDEX check_runs_check ON check_runs(check_id, id);
