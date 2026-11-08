use crate::observations::{HOST, RESUME_SESSIONS, SessionSummary, session_summaries};
use crate::{MemoryStore, invalid, nonblank, retry_busy};
use rusqlite::{OptionalExtension, Result, params};
use serde::Serialize;

/// Höchstzahl unerledigter Aufgaben im Fortsetzungsstand.
pub const RESUME_OPEN_TASKS: usize = 20;
const RESUME_DONE_TASKS: usize = 5;
const RESUME_DECISIONS: usize = 5;
const RESUME_RECENT_EVENTS: usize = 5;
/// Ab so vielen vollen Tagen gilt eine Aufgabe in Arbeit oder blockiert als möglicherweise veraltet.
const STALE_TASK_DAYS: i64 = 2;
const OPEN_HINT_IDS: i64 = 3;

/// Aufgabe im Fortsetzungsstand, deren letzter Status `in_progress` oder `blocked` seit
/// mindestens zwei vollen Tagen unverändert ist. Nur ein Hinweis; der Status bleibt.
#[derive(Debug, Serialize)]
pub struct StaleTask {
    pub id: i64,
    pub task_key: Option<String>,
    pub task_status: Option<String>,
    pub age_days: i64,
}

/// Aktive ungeprüfte Einträge genau dieses Bereichs; nur IDs, keine Texte.
#[derive(Debug, Default, Serialize)]
pub struct OpenHints {
    pub total: i64,
    /// Höchstens drei IDs, neueste zuerst.
    pub newest_ids: Vec<i64>,
}

/// Volle Tage seit `created_at`; `None` bei fehlendem, ungültigem oder künftigem Zeitstempel.
/// `now` ist die julianische Zeit, einmal je Snapshot bestimmt.
fn age_days(conn: &rusqlite::Connection, now: f64, created_at: &str) -> Result<Option<i64>> {
    let then: Option<f64> = conn.query_row("SELECT julianday(?1)", [created_at], |r| r.get(0))?;
    Ok(then
        .map(|t| now - t)
        .filter(|d| d.is_finite() && *d >= 0.0)
        .map(|d| d.floor() as i64))
}

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
    /// Beobachtete Werkzeugaufrufe der letzten Sitzungen, zusammengefasst; nicht geprüft.
    pub observed_sessions: Vec<SessionSummary>,
    pub observation_count: i64,
    /// Reparaturen ohne Vorschlag in diesem Bereich; nur IDs, keine Texte.
    pub open_repairs: crate::OpenRepairs,
    /// Angezeigte Aufgaben, die möglicherweise veraltet sind (siehe `StaleTask`).
    pub stale_tasks: Vec<StaleTask>,
    pub open_hints: OpenHints,
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
/// Wörter der Tagebuchsuche: Folgen alphanumerischer Zeichen, klein geschrieben, ohne Dubletten.
fn journal_words(query: &str) -> Vec<String> {
    let mut words: Vec<String> = Vec::new();
    for word in query
        .split(|c: char| !c.is_alphanumeric())
        .filter(|s| !s.is_empty())
    {
        let word = word.to_lowercase();
        if !words.contains(&word) {
            words.push(word);
        }
    }
    words
}
/// UND-Verknüpfung: jedes Wort muss in body, source oder task_key vorkommen.
fn journal_matches(entry: &JournalEntry, words: &[String]) -> bool {
    let fields = [
        entry.body.to_lowercase(),
        entry.source.to_lowercase(),
        entry.task_key.as_deref().unwrap_or("").to_lowercase(),
    ];
    words
        .iter()
        .all(|word| fields.iter().any(|field| field.contains(word.as_str())))
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
        retry_busy(&self.conn, || {
            self.conn.execute(
                "INSERT INTO project_journal(scope,kind,task_key,task_status,body,source)
                VALUES(?1,?2,?3,?4,?5,?6)",
                params![scope, kind, key, status, body, source],
            )
        })?;
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
    /// Durchsucht nur lesend das Projekttagebuch genau dieses Bereichs, ohne global-Beimischung.
    /// Ein Eintrag passt, wenn jedes Wort des Suchtexts als Teilzeichenfolge in body, source
    /// oder task_key vorkommt. Groß-/Kleinschreibung zählt nicht (auch bei Umlauten), Akzente
    /// werden nicht angeglichen (é ≠ e). Lineare Suche ohne Index, neueste zuerst.
    pub fn journal_search(
        &self,
        scope: &str,
        query: &str,
        limit: usize,
    ) -> Result<Vec<JournalEntry>> {
        bounded(scope, 128)?;
        if query.chars().count() > 2000 {
            return Err(invalid("Suchtext zu lang"));
        }
        if !(1..=20).contains(&limit) {
            return Err(invalid("Limit muss 1 bis 20 sein"));
        }
        let words = journal_words(query);
        if words.is_empty() {
            return Ok(Vec::new());
        }
        // Der Suchtext bleibt reine Daten: SQL filtert nur nach Bereich, Rust nach Wörtern.
        self.read_snapshot(|store| {
            let mut stmt = store.conn.prepare(&format!(
                "SELECT {JOURNAL} FROM project_journal WHERE scope=?1 ORDER BY id DESC"
            ))?;
            let mut found = Vec::new();
            for row in stmt.query_map([scope], entry)? {
                let row = row?;
                if journal_matches(&row, &words) {
                    found.push(row);
                    if found.len() == limit {
                        break;
                    }
                }
            }
            Ok(found)
        })
    }
    pub fn create_conversation(&self, scope: &str, title: &str) -> Result<String> {
        bounded(scope, 128)?;
        bounded(title, 200)?;
        // ID vorab erzeugen und per execute einfügen: execute läuft bis zum Ende, sodass ein
        // Commitfehler sichtbar wird. INSERT ... RETURNING über query_row liest nur die erste
        // Zeile und verschluckt einen späteren Commitfehler (gemeldete ID ohne gespeicherte Zeile).
        let id: String = self
            .conn
            .query_row("SELECT lower(hex(randomblob(16)))", [], |r| r.get(0))?;
        retry_busy(&self.conn, || {
            self.conn.execute(
                "INSERT INTO conversations(id,scope,title) VALUES(?1,?2,?3)",
                params![id, scope, title],
            )
        })?;
        Ok(id)
    }
    pub fn default_conversation(&self, scope: &str) -> Result<String> {
        bounded(scope, 128)?;
        let id = format!("default:{scope}");
        retry_busy(&self.conn, || {
            self.conn.execute("INSERT INTO conversations(id,scope,title) VALUES(?1,?2,'Standardgespräch') ON CONFLICT(id) DO NOTHING",params![id,scope])
        })?;
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
        retry_busy(&self.conn, || {
            self.conn.execute(
                "INSERT INTO chat_messages(conversation_id,role,content) VALUES(?1,?2,?3)",
                params![conversation, role, content],
            )
        })?;
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
        // A surrounding read_snapshot already owns the transaction (e.g. report).
        let tx = self
            .conn
            .is_autocommit()
            .then(|| self.conn.unchecked_transaction())
            .transpose()?;
        let conn = &self.conn;
        let latest = |kind: &str| -> Result<Option<JournalEntry>> {
            conn.query_row(&format!("SELECT {JOURNAL} FROM project_journal WHERE scope=?1 AND kind=?2 ORDER BY id DESC LIMIT 1"),params![scope,kind],entry).optional()
        };
        let goal = latest("goal")?;
        let next_step = latest("next_step")?;
        // Aktueller Stand je Aufgabe: alle unerledigten (bis 20), von den erledigten nur die
        // letzten fünf. Lange Projekte hätten sonst den Kontext kleiner Modelle gefüllt.
        let mut stmt=conn.prepare(&format!("SELECT {JOURNAL} FROM project_journal j
            WHERE scope=?1 AND kind='task' AND (task_status='done')=?2
            AND id=(SELECT max(id) FROM project_journal WHERE scope=j.scope AND task_key=j.task_key AND kind='task')
            ORDER BY id DESC LIMIT ?3"))?;
        let mut tasks = stmt
            .query_map(params![scope, false, RESUME_OPEN_TASKS], entry)?
            .collect::<Result<Vec<_>>>()?;
        tasks.extend(
            stmt.query_map(params![scope, true, RESUME_DONE_TASKS], entry)?
                .collect::<Result<Vec<_>>>()?,
        );
        drop(stmt);
        let task_count = conn.query_row(
            "SELECT count(DISTINCT task_key) FROM project_journal WHERE scope=?1 AND kind='task'",
            [scope],
            |r| r.get(0),
        )?;
        let mut stmt=conn.prepare(&format!("SELECT {JOURNAL} FROM project_journal WHERE scope=?1 AND kind='decision' ORDER BY id DESC LIMIT ?2"))?;
        let decisions = stmt
            .query_map(params![scope, RESUME_DECISIONS], entry)?
            .collect::<Result<Vec<_>>>()?;
        drop(stmt);
        // Ergänzende Ereignisse ohne bereits gezeigte Entscheidungen. Alte Ziel-,
        // Aufgaben- und nächste-Schritt-Versionen sind Historie, kein aktueller
        // Zustand; sie bleiben über journal vollständig lesbar.
        let shown: Vec<i64> = tasks
            .iter()
            .chain(&decisions)
            .chain(goal.iter())
            .chain(next_step.iter())
            .map(|e| e.id)
            .collect();
        let mut stmt = conn.prepare(&format!(
            "SELECT {JOURNAL} FROM project_journal j WHERE scope=?1
             AND (kind NOT IN ('goal','task','next_step') OR
                  (kind='task' AND id=(SELECT max(previous.id) FROM project_journal previous
                   WHERE previous.scope=j.scope AND previous.kind='task' AND previous.task_key=j.task_key)))
             ORDER BY id DESC LIMIT ?2"
        ))?;
        let candidates = stmt
            .query_map(params![scope, RESUME_RECENT_EVENTS + shown.len()], entry)?
            .collect::<Result<Vec<_>>>()?;
        let mut recent_events: Vec<JournalEntry> = candidates
            .into_iter()
            .filter(|e| !shown.contains(&e.id))
            .take(RESUME_RECENT_EVENTS)
            .collect();
        recent_events.reverse();
        drop(stmt);
        let total_events = conn.query_row(
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
        let mut stmt=conn.prepare("SELECT id,conversation_id,role,content,created_at FROM chat_messages WHERE conversation_id=?1 ORDER BY id DESC LIMIT 10")?;
        let mut chat_tail = stmt
            .query_map([&conversation_id], message)?
            .collect::<Result<Vec<_>>>()?;
        chat_tail.reverse();
        drop(stmt);
        let message_count = found.as_ref().map_or(0, |c| c.message_count);
        let conversation_id = found.map(|c| c.id);
        let observed_sessions = session_summaries(conn, scope, RESUME_SESSIONS)?;
        let observation_count = conn.query_row(
            "SELECT count(*) FROM observations WHERE scope=?1 AND host=?2",
            params![scope, HOST],
            |r| r.get(0),
        )?;
        let open_repairs = self.open_repairs(scope)?;
        let now: f64 = conn.query_row("SELECT julianday('now')", [], |r| r.get(0))?;
        let mut stale_tasks = Vec::new();
        for t in &tasks {
            if !matches!(t.task_status.as_deref(), Some("in_progress" | "blocked")) {
                continue;
            }
            if let Some(age) = age_days(conn, now, &t.created_at)?
                && age >= STALE_TASK_DAYS
            {
                stale_tasks.push(StaleTask {
                    id: t.id,
                    task_key: t.task_key.clone(),
                    task_status: t.task_status.clone(),
                    age_days: age,
                });
            }
        }
        let active_pending = "FROM memories m WHERE m.scope=?1 AND m.status='pending'
            AND NOT EXISTS(SELECT 1 FROM invalidations i WHERE i.memory_id=m.id)";
        let open_hints = OpenHints {
            total: conn.query_row(&format!("SELECT count(*) {active_pending}"), [scope], |r| {
                r.get(0)
            })?,
            newest_ids: conn
                .prepare(&format!(
                    "SELECT m.id {active_pending} ORDER BY m.id DESC LIMIT ?2"
                ))?
                .query_map(params![scope, OPEN_HINT_IDS], |r| r.get(0))?
                .collect::<Result<_>>()?,
        };
        if let Some(tx) = tx {
            tx.commit()?;
        }
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
            observed_sessions,
            observation_count,
            open_repairs,
            stale_tasks,
            open_hints,
        })
    }
}
