-- Neuer Entwurf; die Migration aus dem früheren Chat war nicht verfügbar.
CREATE TABLE memories (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('error_solution', 'long_term')),
    problem TEXT NOT NULL CHECK (length(trim(problem)) > 0),
    solution TEXT NOT NULL CHECK (length(trim(solution)) > 0),
    source TEXT NOT NULL CHECK (length(trim(source)) > 0),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'validated')),
    validated_by TEXT,
    evidence TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (
        (status = 'pending' AND validated_by IS NULL AND evidence IS NULL)
        OR (status = 'validated' AND validated_by IS NOT NULL
            AND evidence IS NOT NULL AND length(trim(validated_by)) > 0
            AND length(trim(evidence)) > 0)
    )
) STRICT;
CREATE INDEX memories_status_kind ON memories(status, kind);
