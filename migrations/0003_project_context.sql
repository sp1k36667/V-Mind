-- Projektarbeit und Gespräche sind Verlaufsdaten, kein validiertes Fachwissen.
CREATE TABLE project_journal (
    id INTEGER PRIMARY KEY,
    scope TEXT NOT NULL CHECK(length(trim(scope))>0),
    kind TEXT NOT NULL CHECK(kind IN ('goal','task','decision','next_step','note')),
    task_key TEXT,
    task_status TEXT CHECK(task_status IN ('open','in_progress','done','blocked')),
    body TEXT NOT NULL CHECK(length(trim(body))>0),
    source TEXT NOT NULL CHECK(length(trim(source))>0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    CHECK((kind='task' AND task_key IS NOT NULL AND length(trim(task_key))>0 AND task_status IS NOT NULL)
        OR (kind<>'task' AND task_key IS NULL AND task_status IS NULL))
) STRICT;
CREATE INDEX project_journal_scope ON project_journal(scope,id);
CREATE INDEX project_journal_task ON project_journal(scope,task_key,id);
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL CHECK(length(trim(scope))>0),
    title TEXT NOT NULL CHECK(length(trim(title))>0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
) STRICT;
CREATE INDEX conversations_scope ON conversations(scope,created_at,id);
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL CHECK(role IN ('user','assistant','tool')),
    content TEXT NOT NULL CHECK(length(trim(content))>0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
) STRICT;
CREATE INDEX chat_messages_conversation ON chat_messages(conversation_id,id);
