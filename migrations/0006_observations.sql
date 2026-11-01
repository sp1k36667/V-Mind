-- Beobachtungen eines Hosts (zunächst nur Claude Code): welches Werkzeug lief, ob es
-- abgeschlossen oder fehlgeschlagen ist und welche Projektdateien betroffen waren.
-- Bewusst getrennt vom Projekttagebuch: viele kurze Einträge, nie Befehle, Ausgaben
-- oder Dateiinhalte. Ein abgeschlossener Aufruf ist kein bestandener Test.
CREATE TABLE observations (
    id INTEGER PRIMARY KEY,
    scope TEXT NOT NULL CHECK(length(trim(scope))>0 AND length(scope)<=128),
    host TEXT NOT NULL CHECK(host='claude-code'),
    session_id TEXT NOT NULL CHECK(length(trim(session_id))>0 AND length(session_id)<=200),
    tool_use_id TEXT NOT NULL CHECK(length(trim(tool_use_id))>0 AND length(tool_use_id)<=200),
    tool TEXT NOT NULL CHECK(tool IN ('Bash','Edit','Write')),
    result TEXT NOT NULL CHECK(result IN ('completed','failed')),
    paths TEXT NOT NULL CHECK(json_valid(paths) AND json_type(paths)='array'),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE(host, session_id, tool_use_id)
);
CREATE INDEX observations_scope_session ON observations(scope, session_id, id);
