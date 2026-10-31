use crate::{MemoryStore, invalid, nonblank};
use rusqlite::{OptionalExtension, Result, params};
use serde::Serialize;

#[derive(Debug, Serialize)]
pub struct JournalEntry {
    pub id: i64,
    pub scope: String,
    pub kind: String,
    pub task_key: Option<String>,
    pub task_status: Option<String>,
    pub body: String,
    pub source: String,
    pub created_at: String,
}
#[derive(Debug, Serialize)]
pub struct ChatMessage {
    pub id: i64,
    pub conversation_id: String,
    pub role: String,
    pub content: String,
    pub created_at: String,
}
#[derive(Debug, Serialize)]
pub struct Conversation {
    pub id: String,
    pub scope: String,
    pub title: String,
    pub created_at: String,
    pub message_count: i64,
}
#[derive(Debug, Serialize)]
pub struct Resume {
    pub scope: String,
    pub goal: Option<JournalEntry>,
    pub next_step: Option<JournalEntry>,
    pub tasks: Vec<JournalEntry>,
    pub task_count: i64,
    pub decisions: Vec<JournalEntry>,
    pub recent_events: Vec<JournalEntry>,
    pub total_events: i64,
    pub conversation_id: Option<String>,
    pub chat_tail: Vec<ChatMessage>,
    pub message_count: i64,
}
const JOURNAL: &str = "id,scope,kind,task_key,task_status,body,source,created_at";
fn entry(r: &rusqlite::Row<'_>) -> Result<JournalEntry> {
    Ok(JournalEntry {
        id: r.get(0)?,
        scope: r.get(1)?,
        kind: r.get(2)?,
        task_key: r.get(3)?,
        task_status: r.get(4)?,
        body: r.get(5)?,
        source: r.get(6)?,
        created_at: r.get(7)?,
    })
}
fn message(r: &rusqlite::Row<'_>) -> Result<ChatMessage> {
    Ok(ChatMessage {
        id: r.get(0)?,
        conversation_id: r.get(1)?,
        role: r.get(2)?,
        content: r.get(3)?,
        created_at: r.get(4)?,
    })
}
fn bounded(value: &str, max: usize) -> Result<()> {
    nonblank(value)?;
    if value.chars().count() > max {
        return Err(invalid("Größenlimit für Projektkontext überschritten"));
    }
    Ok(())
}
fn page(after: i64, limit: usize) -> Result<()> {
    if after < 0 || !(1..=100).contains(&limit) {
        return Err(invalid("Cursor muss >=0 und Limit 1 bis 100 sein"));
    }
    Ok(())
}
impl MemoryStore {
    /// Append-only Ereignis; task_key bezeichnet dieselbe Aufgabe über mehrere Statuswechsel.
    pub fn journal(
        &self,
        scope: &str,
        kind: &str,
        key: Option<&str>,
        status: Option<&str>,
        body: &str,
        source: &str,
    ) -> Result<i64> {
        bounded(scope, 128)?;
        bounded(body, 16000)?;
        bounded(source, 4000)?;
        if let Some(key) = key {
            bounded(key, 128)?;
        }
        self.conn.execute(
            "INSERT INTO project_journal(scope,kind,task_key,task_status,body,source)
            VALUES(?1,?2,?3,?4,?5,?6)",
            params![scope, kind, key, status, body, source],
        )?;
        Ok(self.conn.last_insert_rowid())
    }
    pub fn journal_page(&self, scope: &str, after: i64, limit: usize) -> Result<Vec<JournalEntry>> {
        bounded(scope, 128)?;
        page(after, limit)?;
        let mut stmt = self.conn.prepare(&format!(
            "SELECT {JOURNAL} FROM project_journal WHERE scope=?1 AND id>?2 ORDER BY id LIMIT ?3"
        ))?;
        stmt.query_map(params![scope, after, limit as i64], entry)?
            .collect()
    }
    pub fn create_conversation(&self, scope: &str, title: &str) -> Result<String> {
        bounded(scope, 128)?;
        bounded(title, 200)?;
        self.conn.query_row("INSERT INTO conversations(id,scope,title) VALUES(lower(hex(randomblob(16))),?1,?2) RETURNING id",
            params![scope,title],|r|r.get(0))
    }
    pub fn default_conversation(&self, scope: &str) -> Result<String> {
        bounded(scope, 128)?;
        let id = format!("default:{scope}");
        self.conn.execute("INSERT INTO conversations(id,scope,title) VALUES(?1,?2,'Standardgespräch') ON CONFLICT(id) DO NOTHING",params![id,scope])?;
        Ok(id)
    }
    pub fn conversation(&self, id: &str) -> Result<Option<Conversation>> {
        self.conn
            .query_row(
                "SELECT id,scope,title,created_at,
            (SELECT count(*) FROM chat_messages WHERE conversation_id=conversations.id)
            FROM conversations WHERE id=?1",
                [id],
                |r| {
                    Ok(Conversation {
                        id: r.get(0)?,
                        scope: r.get(1)?,
                        title: r.get(2)?,
                        created_at: r.get(3)?,
                        message_count: r.get(4)?,
                    })
                },
            )
            .optional()
    }
    pub fn conversations(&self, scope: &str) -> Result<Vec<Conversation>> {
        bounded(scope, 128)?;
        let mut stmt = self.conn.prepare(
            "SELECT id,scope,title,created_at,
            (SELECT count(*) FROM chat_messages WHERE conversation_id=conversations.id)
            FROM conversations WHERE scope=?1 ORDER BY created_at DESC,id DESC LIMIT 100",
        )?;
        stmt.query_map([scope], |r| {
            Ok(Conversation {
                id: r.get(0)?,
                scope: r.get(1)?,
                title: r.get(2)?,
                created_at: r.get(3)?,
                message_count: r.get(4)?,
            })
        })?
        .collect()
    }
    pub fn append_message(&self, conversation: &str, role: &str, content: &str) -> Result<i64> {
        bounded(content, 32000)?;
        self.conn.execute(
            "INSERT INTO chat_messages(conversation_id,role,content) VALUES(?1,?2,?3)",
            params![conversation, role, content],
        )?;
        Ok(self.conn.last_insert_rowid())
    }
    pub fn messages(
        &self,
        conversation: &str,
        after: i64,
        limit: usize,
    ) -> Result<Vec<ChatMessage>> {
        page(after, limit)?;
        if self.conversation(conversation)?.is_none() {
            return Err(invalid("Gespräch nicht gefunden"));
        }
        let mut stmt = self.conn.prepare(
            "SELECT id,conversation_id,role,content,created_at FROM chat_messages
            WHERE conversation_id=?1 AND id>?2 ORDER BY id LIMIT ?3",
        )?;
        stmt.query_map(params![conversation, after, limit as i64], message)?
            .collect()
    }
    /// Snapshot in einer Lesetransaktion. Projektkontext ist exakt bereichsgebunden, ohne global-Beimischung.
    pub fn resume(&self, scope: &str, conversation: Option<&str>) -> Result<Resume> {
        bounded(scope, 128)?;
        let tx = self.conn.unchecked_transaction()?;
        let latest = |kind: &str| -> Result<Option<JournalEntry>> {
            tx.query_row(&format!("SELECT {JOURNAL} FROM project_journal WHERE scope=?1 AND kind=?2 ORDER BY id DESC LIMIT 1"),params![scope,kind],entry).optional()
        };
        let goal = latest("goal")?;
        let next_step = latest("next_step")?;
        let mut stmt=tx.prepare(&format!("SELECT {JOURNAL} FROM project_journal j
            WHERE scope=?1 AND kind='task' AND id=(SELECT max(id) FROM project_journal WHERE scope=j.scope AND task_key=j.task_key AND kind='task')
            ORDER BY CASE WHEN task_status='done' THEN 1 ELSE 0 END,id DESC LIMIT 20"))?;
        let tasks = stmt
            .query_map([scope], entry)?
            .collect::<Result<Vec<_>>>()?;
        drop(stmt);
        let task_count = tx.query_row(
            "SELECT count(DISTINCT task_key) FROM project_journal WHERE scope=?1 AND kind='task'",
            [scope],
            |r| r.get(0),
        )?;
        let mut stmt=tx.prepare(&format!("SELECT {JOURNAL} FROM project_journal WHERE scope=?1 AND kind='decision' ORDER BY id DESC LIMIT 10"))?;
        let decisions = stmt
            .query_map([scope], entry)?
            .collect::<Result<Vec<_>>>()?;
        drop(stmt);
        let mut stmt = tx.prepare(&format!(
            "SELECT {JOURNAL} FROM project_journal WHERE scope=?1 ORDER BY id DESC LIMIT 10"
        ))?;
        let mut recent_events = stmt
            .query_map([scope], entry)?
            .collect::<Result<Vec<_>>>()?;
        recent_events.reverse();
        drop(stmt);
        let total_events = tx.query_row(
            "SELECT count(*) FROM project_journal WHERE scope=?1",
            [scope],
            |r| r.get(0),
        )?;
        let conversation_id = conversation
            .map(String::from)
            .unwrap_or_else(|| format!("default:{scope}"));
        let found = self.conversation(&conversation_id)?;
        if conversation.is_some() && found.is_none() {
            return Err(invalid("Gespräch nicht gefunden"));
        }
        if found.as_ref().is_some_and(|c| c.scope != scope) {
            return Err(invalid("Gespräch gehört zu anderem Projektbereich"));
        }
        let mut stmt=tx.prepare("SELECT id,conversation_id,role,content,created_at FROM chat_messages WHERE conversation_id=?1 ORDER BY id DESC LIMIT 10")?;
        let mut chat_tail = stmt
            .query_map([&conversation_id], message)?
            .collect::<Result<Vec<_>>>()?;
        chat_tail.reverse();
        drop(stmt);
        let message_count = found.as_ref().map_or(0, |c| c.message_count);
        let conversation_id = found.map(|c| c.id);
        tx.commit()?;
        Ok(Resume {
            scope: scope.into(),
            goal,
            next_step,
            tasks,
            task_count,
            decisions,
            recent_events,
            total_events,
            conversation_id,
            chat_tail,
            message_count,
        })
    }
}
