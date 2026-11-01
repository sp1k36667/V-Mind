mod check_cmd;
mod mcp;
mod observe;
mod ollama;
mod prompt;
mod protocol;
mod report;
mod runner;

use serde::Serialize;
use serde_json::json;
use std::{env, error::Error, io};
use vmind_core::{MemoryStore, Record};

type Result<T> = std::result::Result<T, Box<dyn Error>>;
const HELP: &str = "V-Mind – lokales Gedächtnis für KI-Werkzeuge
Aufruf: vmind [--json] [--scope BEREICH] BEFEHL ...
  start-prompt                  (Startanweisung für die nutzende KI)
  init DB
  doctor DB                     (nur lesen: Schema, Integrität, Fremdschlüssel)
  backup DB ZIEL                (geprüfte SQLite-Sicherung, überschreibt niemals)
  add DB error_solution|long_term PROBLEM LÖSUNG QUELLE
  pending DB
  show DB ID
  validate DB ID PRÜFER NACHWEIS
  invalidate DB ID AKTEUR GRUND
  check-set DB ID AKTEUR ORDNER BEFEHL [ARG...]   (Prüfbefehl ohne Shell setzen)
  check DB ID [--invalidate]     (Prüfbefehl ausführen; bestanden validiert)
  revalidate DB [--invalidate]   (alle Prüfbefehle im Bereich plus global)
  search DB WÖRTLICHER_SUCHTEXT   (globale Einträge)
  recall DB SUCHTEXT             (Volltext, Projekt plus global)
  ask DB FRAGE                  (automatischer Wissensabruf)
  ask DB SUCHTEXT FRAGE          (expliziter Wissensabruf)
  stats DB
  journal DB                    (erste 100 Projektereignisse)
  journal DB NACH_ID             (nächste Seite)
  log DB goal|decision|next_step|note TEXT QUELLE
  task DB SCHLÜSSEL open|in_progress|done|blocked TEXT QUELLE
  resume DB                     (Fortsetzungsstand des Projektbereichs)
  resume DB GESPRÄCH_ID
  report DB                     (lesbarer Projektbericht in Markdown, nur lesen)
  observe DB                    (Claude-Code-Hook: Meldung von stdin, nur Werkzeug/Ergebnis/Pfad)
  sessions DB
  session-new DB TITEL
  messages DB GESPRÄCH_ID [NACH_ID]
  chat DB GESPRÄCH_ID FRAGE
  serve DB                      (JSONL-Protokoll v1 über stdin/stdout)
  mcp DB                        (MCP-Server über stdio; --scope = Standardbereich)
DB bezeichnet einen Dateipfad, keine SQLite-URI.
Standardbereich: VMIND_SCOPE oder global.
Ollama: VMIND_OLLAMA_URL oder http://127.0.0.1:11434
Modell: VMIND_MODEL oder vmind-gemma4:e2b
Zeitlimit für Prüfbefehle: VMIND_CHECK_TIMEOUT Sekunden, sonst 300";

fn emit(value: impl Serialize, human: String, json_mode: bool) -> Result<()> {
    if json_mode {
        println!("{}", serde_json::to_string(&value)?);
    } else {
        println!("{human}");
    }
    Ok(())
}
fn summary(records: &[Record]) -> String {
    if records.is_empty() {
        return "Keine Einträge gefunden.".into();
    }
    records
        .iter()
        .map(|r| {
            format!(
                "#{} [{} / {} / {}]\n{}\n→ {}\nQuelle: {}\nPrüfer: {}\nNachweis: {}\nPrüfzustand: {}",
                r.id,
                r.scope,
                r.kind,
                r.status,
                r.problem,
                r.solution,
                r.source,
                r.validated_by.as_deref().unwrap_or("–"),
                r.evidence.as_deref().unwrap_or("–"),
                check_cmd::evidence_note(&r.check)
            )
        })
        .collect::<Vec<_>>()
        .join("\n\n")
}
fn require_change(changed: bool) -> Result<()> {
    if changed {
        Ok(())
    } else {
        Err(io::Error::other("Eintrag fehlt oder Statusänderung nicht zulässig.").into())
    }
}
fn ask(
    db: &str,
    scope: &str,
    query: &str,
    question: &str,
    session: Option<&str>,
    json_mode: bool,
) -> Result<()> {
    if question.trim().is_empty() || question.chars().count() > 2000 {
        return Err(io::Error::other("Die Frage muss 1 bis 2000 Zeichen enthalten.").into());
    }
    let store = MemoryStore::open_existing(db)?;
    let session = match session {
        Some(s) => s.into(),
        None => store.default_conversation(scope)?,
    };
    let resume = store.resume(scope, Some(&session))?;
    let memories = store.recall(query, scope, 3)?;
    let endpoint = env::var("VMIND_OLLAMA_URL").unwrap_or_else(|_| "http://127.0.0.1:11434".into());
    let model = env::var("VMIND_MODEL").unwrap_or_else(|_| "vmind-gemma4:e2b".into());
    if !json_mode {
        eprintln!(
            "Gespräch {session}: {} frühere Nachrichten, {} Projektereignisse, {} Wissenseinträge.",
            resume.message_count,
            resume.total_events,
            memories.len()
        );
    }
    let user_id = store.append_message(&session, "user", question)?;
    let answer = match ollama::generate(&endpoint, &model, question, &memories, Some(&resume)) {
        Ok(answer) => answer,
        Err(error) => {
            store.append_message(
                &session,
                "tool",
                &format!("Modellanfrage für Nachricht {user_id} fehlgeschlagen: {error}"),
            )?;
            return Err(error);
        }
    };
    let assistant_id = store.append_message(&session, "assistant", &answer)?;
    emit(
        json!({"answer":answer,"retrieved_memories":memories,"model":model,
        "answer_status":"unvalidated","scope":scope,"conversation_id":session,
        "user_message_id":user_id,"assistant_message_id":assistant_id}),
        answer.clone(),
        json_mode,
    )
}
fn resume_output(db: &str, scope: &str, session: Option<&str>, json_mode: bool) -> Result<()> {
    let resume = MemoryStore::open_existing(db)?.resume(scope, session)?;
    let tasks = resume
        .tasks
        .iter()
        .map(|t| {
            format!(
                "- [{}] {}: {}",
                t.task_status.as_deref().unwrap_or("?"),
                t.task_key.as_deref().unwrap_or("?"),
                t.body
            )
        })
        .collect::<Vec<_>>()
        .join("\n");
    let decisions = resume
        .decisions
        .iter()
        .map(|d| format!("- {} (Quelle: {})", d.body, d.source))
        .collect::<Vec<_>>()
        .join("\n");
    let messages = resume
        .chat_tail
        .iter()
        .map(|m| format!("{}: {}", m.role, m.content))
        .collect::<Vec<_>>()
        .join("\n");
    let text = format!(
        "Projekt: {}\nZiel: {}\n\nAufgaben ({} von {}):\n{}\n\nEntscheidungen:\n{}\n\nNächster Schritt: {}\n\nLetzte Nachrichten ({} von {}):\n{}\n\nGespeicherte Projektereignisse: {}. Vollständige Historie: journal / messages.",
        resume.scope,
        resume
            .goal
            .as_ref()
            .map_or("Noch kein Ziel gespeichert", |e| e.body.as_str()),
        resume.tasks.len(),
        resume.task_count,
        tasks,
        decisions,
        resume
            .next_step
            .as_ref()
            .map_or("Noch nicht festgelegt", |e| e.body.as_str()),
        resume.chat_tail.len(),
        resume.message_count,
        messages,
        resume.total_events
    );
    let text = if resume.observation_count == 0 {
        text
    } else {
        format!(
            "{text}\n\nBeobachtete Werkzeugaufrufe (nicht geprüft; {} insgesamt):\n{}",
            resume.observation_count,
            observed_lines(&resume.observed_sessions).join("\n")
        )
    };
    emit(resume, text, json_mode)
}

/// Eine Zeile je Sitzung. Ein abgeschlossener Aufruf heißt nicht, dass ein Test bestand.
pub(crate) fn observed_lines(sessions: &[vmind_core::SessionSummary]) -> Vec<String> {
    sessions
        .iter()
        .map(|s| {
            format!(
                "- Sitzung {} ({} bis {}): {} Aufrufe, davon {} fehlgeschlagen; {} Dateien{}",
                s.session_id.chars().take(8).collect::<String>(),
                s.first_at,
                s.last_at,
                s.calls,
                s.failed,
                s.files,
                if s.paths.is_empty() {
                    String::new()
                } else {
                    format!(", zuletzt: {}", s.paths.join(", "))
                }
            )
        })
        .collect()
}

fn run() -> Result<()> {
    let mut args: Vec<String> = env::args().skip(1).collect();
    let mut json_mode = false;
    let mut explicit_scope = env::var("VMIND_SCOPE").ok();
    while let Some(arg) = args.first() {
        match arg.as_str() {
            "--json" => {
                json_mode = true;
                args.remove(0);
            }
            "--scope" if args.len() >= 2 => {
                explicit_scope = Some(args.remove(1));
                args.remove(0);
            }
            _ => break,
        }
    }
    let scope = explicit_scope.clone().unwrap_or_else(|| "global".into());
    match args.as_slice() {
        [] => println!("{HELP}"),
        [cmd] if cmd == "--help" || cmd == "help" => println!("{HELP}"),
        [cmd] if cmd == "start-prompt" => emit(
            json!({"prompt":prompt::START_PROMPT}),
            prompt::START_PROMPT.into(),
            json_mode,
        )?,
        [cmd] if cmd == "--version" => println!("vmind {}", env!("CARGO_PKG_VERSION")),
        [cmd, db] if cmd == "doctor" => {
            let report = vmind_core::inspect_database(db)?;
            let healthy = report.healthy;
            let human = format!(
                "Schema {} (unterstützt bis {}), Zustand: {}, Upgrade nötig: {}",
                report.schema_version,
                report.supported_schema_version,
                if healthy {
                    "ok"
                } else {
                    "Fehler – JSON-Bericht prüfen"
                },
                report.migration_required
            );
            emit(report, human, json_mode)?;
            if !healthy {
                return Err(io::Error::other("Datenbankprüfung fehlgeschlagen").into());
            }
        }
        [cmd, db] if cmd == "observe" => observe::run(db, &scope)?,
        [cmd, db] if cmd == "report" => {
            let report = report::build(&MemoryStore::open_read_only(db)?, &scope)?;
            let text = report::markdown(&report);
            emit(report, text, json_mode)?;
        }
        [cmd, db, destination] if cmd == "backup" => {
            let report = vmind_core::backup_database(db, destination)?;
            let human = format!(
                "Geprüfte Sicherung: {} (Schema {}, {} Bytes)",
                report.destination, report.schema_version, report.bytes
            );
            emit(report, human, json_mode)?;
        }
        [cmd, db] if cmd == "init" => {
            let stats = MemoryStore::open_file(db)?.stats(&scope)?;
            emit(
                json!({"database":db,"schema_version":stats.schema_version}),
                format!("Datenbank bereit: {db} (Schema {})", stats.schema_version),
                json_mode,
            )?;
        }
        [cmd, db, kind, problem, solution, source] if cmd == "add" => {
            let id = MemoryStore::open_existing(db)?
                .remember_scoped(&scope, kind, problem, solution, source)?;
            emit(
                json!({"id":id,"status":"pending","scope":scope}),
                format!("Eintrag {id} gespeichert (pending, {scope})."),
                json_mode,
            )?;
        }
        [cmd, db, id, reviewer, evidence] if cmd == "validate" => {
            require_change(MemoryStore::open_existing(db)?.validate(
                id.parse()?,
                reviewer,
                evidence,
            )?)?;
            emit(
                json!({"id":id.parse::<i64>()?,"status":"validated"}),
                "Validierung dokumentiert.".into(),
                json_mode,
            )?;
        }
        [cmd, db, id, actor, reason] if cmd == "invalidate" => {
            require_change(MemoryStore::open_existing(db)?.invalidate(
                id.parse()?,
                actor,
                reason,
            )?)?;
            emit(
                json!({"id":id.parse::<i64>()?,"status":"invalidated"}),
                "Eintrag zurückgezogen; Historie bleibt erhalten.".into(),
                json_mode,
            )?;
        }
        [cmd, db, id] if cmd == "show" => {
            let store = MemoryStore::open_existing(db)?;
            let id = id.parse()?;
            let memory = store
                .get(id)?
                .ok_or_else(|| io::Error::other("Eintrag nicht gefunden"))?;
            let history = store.history(id)?;
            let check = store.active_check(id)?;
            let runs = store.check_runs(id, 5)?;
            let check_text = check.as_ref().map_or("–".to_string(), |c| {
                format!("#{} `{}` in {}", c.id, c.command_line(), c.workdir)
            });
            let human = format!(
                "{}\nErstellt: {}\nZurückgezogen durch: {}\nGrund: {}\nPrüfbefehl: {}\n\nHistorie:\n{}\n\nLetzte Prüfläufe:\n{}",
                summary(std::slice::from_ref(&memory)),
                memory.created_at,
                memory.invalidated_by.as_deref().unwrap_or("–"),
                memory.invalidation_reason.as_deref().unwrap_or("–"),
                check_text,
                history
                    .iter()
                    .map(|e| format!("{} {} / {}: {}", e.created_at, e.action, e.actor, e.reason))
                    .collect::<Vec<_>>()
                    .join("\n"),
                runs.iter()
                    .map(|r| format!(
                        "{} {} (Exit {}, {} ms)",
                        r.created_at,
                        r.outcome,
                        r.exit_code.map_or("–".into(), |c| c.to_string()),
                        r.duration_ms
                    ))
                    .collect::<Vec<_>>()
                    .join("\n")
            );
            emit(
                json!({"memory":memory,"history":history,"check":check,"check_runs":runs}),
                human,
                json_mode,
            )?;
        }
        [cmd, db, id, actor, dir, argv @ ..] if cmd == "check-set" && !argv.is_empty() => {
            check_cmd::set(db, id, actor, dir, argv, json_mode)?
        }
        [cmd, db, id] if cmd == "check" => check_cmd::check_one(db, id, false, json_mode)?,
        [cmd, db, id, flag] if cmd == "check" && flag == "--invalidate" => {
            check_cmd::check_one(db, id, true, json_mode)?
        }
        [cmd, db] if cmd == "revalidate" => check_cmd::revalidate(db, &scope, false, json_mode)?,
        [cmd, db, flag] if cmd == "revalidate" && flag == "--invalidate" => {
            check_cmd::revalidate(db, &scope, true, json_mode)?
        }
        [cmd, db] if cmd == "pending" => {
            let records = MemoryStore::open_existing(db)?.pending(&scope)?;
            emit(&records, summary(&records), json_mode)?;
        }
        [cmd, db] if cmd == "stats" => {
            let stats = MemoryStore::open_existing(db)?.stats(&scope)?;
            let human = format!(
                "Bereich: {scope} + global\nSchema: {}\nUngeprüft: {}\nValidiert: {}\nZurückgezogen: {}",
                stats.schema_version, stats.pending, stats.validated, stats.invalidated
            );
            emit(stats, human, json_mode)?;
        }
        [cmd, db, query] if cmd == "search" => {
            let memories = MemoryStore::open_existing(db)?.search(query)?;
            let human = memories
                .iter()
                .map(|m| format!("#{} [{}] {} → {}", m.id, m.kind, m.problem, m.solution))
                .collect::<Vec<_>>()
                .join("\n");
            emit(memories, human, json_mode)?;
        }
        [cmd, db, query] if cmd == "recall" => {
            let records = MemoryStore::open_existing(db)?.recall(query, &scope, 5)?;
            emit(&records, summary(&records), json_mode)?;
        }
        [cmd, db, question] if cmd == "ask" => {
            ask(db, &scope, question, question, None, json_mode)?
        }
        [cmd, db, query, question] if cmd == "ask" => {
            ask(db, &scope, query, question, None, json_mode)?
        }
        [cmd, db, session, question] if cmd == "chat" => {
            ask(db, &scope, question, question, Some(session), json_mode)?
        }
        [cmd, db] if cmd == "resume" => resume_output(db, &scope, None, json_mode)?,
        [cmd, db, session] if cmd == "resume" => {
            resume_output(db, &scope, Some(session), json_mode)?
        }
        [cmd, db, title] if cmd == "session-new" => {
            let id = MemoryStore::open_existing(db)?.create_conversation(&scope, title)?;
            emit(
                json!({"conversation_id":id,"scope":scope}),
                format!("Gespräch angelegt: {id}"),
                json_mode,
            )?;
        }
        [cmd, db] if cmd == "sessions" => {
            let sessions = MemoryStore::open_existing(db)?.conversations(&scope)?;
            let text = sessions
                .iter()
                .map(|s| format!("{}: {} ({} Nachrichten)", s.id, s.title, s.message_count))
                .collect::<Vec<_>>()
                .join("\n");
            emit(sessions, text, json_mode)?;
        }
        [cmd, db, session] if cmd == "messages" => {
            let messages = MemoryStore::open_existing(db)?.messages(session, 0, 100)?;
            let text = serde_json::to_string_pretty(&messages)?;
            emit(messages, text, json_mode)?;
        }
        [cmd, db, session, after] if cmd == "messages" => {
            let messages =
                MemoryStore::open_existing(db)?.messages(session, after.parse()?, 100)?;
            let text = serde_json::to_string_pretty(&messages)?;
            emit(messages, text, json_mode)?;
        }
        [cmd, db, kind, body, source] if cmd == "log" => {
            let id =
                MemoryStore::open_existing(db)?.journal(&scope, kind, None, None, body, source)?;
            emit(
                json!({"event_id":id}),
                format!("Projektereignis {id} gespeichert."),
                json_mode,
            )?;
        }
        [cmd, db, key, status, body, source] if cmd == "task" => {
            let id = MemoryStore::open_existing(db)?.journal(
                &scope,
                "task",
                Some(key),
                Some(status),
                body,
                source,
            )?;
            emit(
                json!({"event_id":id,"task_key":key,"status":status}),
                format!("Aufgabe {key}: {status} (Ereignis {id})."),
                json_mode,
            )?;
        }
        [cmd, db] if cmd == "journal" => {
            let events = MemoryStore::open_existing(db)?.journal_page(&scope, 0, 100)?;
            let text = serde_json::to_string_pretty(&events)?;
            emit(events, text, json_mode)?;
        }
        [cmd, db, after] if cmd == "journal" => {
            let events =
                MemoryStore::open_existing(db)?.journal_page(&scope, after.parse()?, 100)?;
            let text = serde_json::to_string_pretty(&events)?;
            emit(events, text, json_mode)?;
        }
        [cmd, db] if cmd == "serve" => {
            protocol::serve(
                &MemoryStore::open_existing(db)?,
                io::stdin().lock(),
                io::stdout().lock(),
            )?;
        }
        [cmd, db] if cmd == "mcp" => {
            mcp::serve(
                &MemoryStore::open_existing(db)?,
                explicit_scope.as_deref(),
                io::stdin().lock(),
                io::stdout().lock(),
            )?;
        }
        _ => return Err(io::Error::other(HELP).into()),
    }
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("V-Mind: {error}");
        std::process::exit(1);
    }
}
