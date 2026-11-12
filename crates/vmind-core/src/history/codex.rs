//! Deutung der Rollout-Dateien von Codex. Auch dieses Format ist keine offizielle
//! Schnittstelle. Übernommen werden nur `event_msg/item_completed` mit `UserMessage` (mit
//! nichtleerer `client_id`) und synchronem `AgentMessage` der Phase `final_answer`; die
//! doppelte Darstellung in `response_item`, Werkzeuge, Kontext und Kompaktierung nie.
use super::{
    LineOutcome, MAX_ID_CHARS, MAX_TIMESTAMP_CHARS, Message, bounded_id, required_id, stored_text,
};
use serde_json::Value;
use std::{borrow::Cow, collections::HashMap};

/// Kontexthüllen, die Codex oder eine App in Nutzertext einbettet; nur belegte Tagnamen.
/// Der öffnende Tag darf Attribute tragen (`<in-app-browser-context source="…">`). Andere
/// Tags bleiben Text, auch ähnlich benannte.
const APP_ENVELOPES: [&str; 2] = ["app-context", "in-app-browser-context"];

/// Sitzung und Turn-Zuordnung. Ein Lauf ab Byte-Stand beginnt mit dem gespeicherten Stand.
#[derive(Default)]
pub(super) struct Cursor {
    session: Option<String>,
    /// `None` als Wert: widersprüchliche Modelle in einem Turn, also nicht belegt.
    turns: HashMap<String, Option<String>>,
    last_turn: Option<(String, Option<String>)>,
}

impl Cursor {
    pub(super) fn resume(
        session: Option<String>,
        turn: Option<String>,
        model: Option<String>,
    ) -> Self {
        let last_turn = turn.map(|turn| (turn, model));
        let turns = last_turn.iter().cloned().collect();
        Self {
            session,
            turns,
            last_turn,
        }
    }

    pub(super) fn session(&self) -> Option<&str> {
        self.session.as_deref()
    }

    pub(super) fn last_turn(&self) -> (Option<&str>, Option<&str>) {
        match &self.last_turn {
            Some((turn, model)) => (Some(turn), model.as_deref()),
            None => (None, None),
        }
    }

    /// Ordnet erst am Ende des Laufs zu: `turn_context` darf auch nach der Nachricht stehen.
    pub(super) fn assign_models(&self, messages: &mut [Message]) {
        for message in messages {
            if let Some(turn) = message.turn_id.take() {
                message.model = self.turns.get(&turn).cloned().flatten();
            }
        }
    }

    fn session_meta(&mut self, row: &Value) -> Result<(), &'static str> {
        let id = required_id(
            &row["payload"],
            "id",
            MAX_ID_CHARS,
            "session_meta ohne gültige Kennung",
        )?;
        if self.session.as_deref().is_some_and(|known| known != id) {
            return Err("Zweite session_meta mit anderer Kennung");
        }
        self.session = Some(id.to_owned());
        Ok(())
    }

    /// Nur eine vollständige Angabe zählt; sie ist Zusatzwissen und hält die Datei nie an.
    fn turn_context(&mut self, row: &Value) {
        let field = |key: &str| {
            row["payload"][key]
                .as_str()
                .filter(|v| bounded_id(v, MAX_ID_CHARS))
                .map(str::to_owned)
        };
        let (Some(turn), Some(model)) = (field("turn_id"), field("model")) else {
            return;
        };
        let known = self
            .turns
            .entry(turn.clone())
            .or_insert_with(|| Some(model.clone()));
        if known.as_ref() != Some(&model) {
            *known = None;
        }
        self.last_turn = Some((turn, known.clone()));
    }

    pub(super) fn parse(&mut self, row: &Value) -> Result<LineOutcome, &'static str> {
        if !row.is_object() {
            return Err("Zeile ist kein JSON-Objekt");
        }
        match row["type"].as_str() {
            None => Err("Zeile ohne Typ"),
            Some("session_meta") => self.session_meta(row).map(|()| LineOutcome::Skip),
            Some("turn_context") => {
                self.turn_context(row);
                Ok(LineOutcome::Skip)
            }
            Some("event_msg") => self.event(row),
            Some(_) => Ok(LineOutcome::Skip),
        }
    }

    fn event(&self, row: &Value) -> Result<LineOutcome, &'static str> {
        let payload = &row["payload"];
        match payload["type"].as_str() {
            None => Err("event_msg ohne Typ"),
            Some("item_completed") => self.completed_item(row, payload),
            Some(_) => Ok(LineOutcome::Skip),
        }
    }

    fn completed_item(&self, row: &Value, payload: &Value) -> Result<LineOutcome, &'static str> {
        let item = &payload["item"];
        let taken = match item["type"].as_str() {
            None => return Err("item_completed ohne Elementtyp"),
            Some("UserMessage") => user_text(item)?.map(|text| ("user", text)),
            Some("AgentMessage") => agent_text(item)?.map(|text| ("assistant", text)),
            Some(_) => None,
        };
        let Some((role, text)) = taken else {
            return Ok(LineOutcome::Skip);
        };
        if text.trim().is_empty() {
            return Ok(LineOutcome::Skip);
        }
        let session = self.session().ok_or("Nachricht vor session_meta")?;
        let created_at = required_id(
            row,
            "timestamp",
            MAX_TIMESTAMP_CHARS,
            "timestamp fehlt oder ist ungültig",
        )?;
        let Some(key) = message_key(row, item)? else {
            return Ok(LineOutcome::Unkeyed);
        };
        let uuid = format!("codex:{session}:{key}");
        if !bounded_id(&uuid, MAX_ID_CHARS) {
            return Err("Nachrichtenkennung zu lang");
        }
        Ok(LineOutcome::Message(Message {
            session_id: session.to_owned(),
            uuid,
            role,
            text: stored_text(&text),
            created_at: created_at.to_owned(),
            model: None,
            turn_id: payload["turn_id"]
                .as_str()
                .filter(|v| bounded_id(v, MAX_ID_CHARS))
                .map(str::to_owned),
        }))
    }
}

/// `item.id` bevorzugt; `ordinal` nur, wenn die ID fehlt, und in einem eigenen Namensraum.
fn message_key(row: &Value, item: &Value) -> Result<Option<String>, &'static str> {
    match item.get("id") {
        None | Some(Value::Null) => match row.get("ordinal") {
            None | Some(Value::Null) => Ok(None),
            Some(value) => {
                let ordinal = value.as_u64().ok_or("ordinal ist keine Ganzzahl")?;
                Ok(Some(format!("ordinal:{ordinal}")))
            }
        },
        Some(Value::String(id)) if bounded_id(id, MAX_ID_CHARS) => Ok(Some(format!("item:{id}"))),
        Some(_) => Err("item.id ist ungültig"),
    }
}

/// Text der Blöcke genau dieses Typs; andere Blöcke (etwa `local_image`) entfallen.
fn blocks_text(content: &Value, kind: &str) -> Result<String, &'static str> {
    let blocks = content.as_array().ok_or("Inhalt ist keine Blockliste")?;
    let mut parts = Vec::new();
    for block in blocks {
        let block_type = block["type"]
            .as_str()
            .ok_or("Inhaltsblock ohne Typ oder kein Objekt")?;
        if block_type == kind {
            parts.push(block["text"].as_str().ok_or("Textblock ohne Text")?);
        }
    }
    Ok(parts.join("\n"))
}

/// Wert eines optionalen Textfelds; ein anderer Typ ist eine unbekannte Struktur.
fn optional_text<'a>(item: &'a Value, key: &str) -> Result<Option<&'a str>, &'static str> {
    match item.get(key) {
        None | Some(Value::Null) => Ok(None),
        Some(Value::String(text)) => Ok(Some(text)),
        Some(_) => Err("Feld hat einen unerwarteten Typ"),
    }
}

fn user_text(item: &Value) -> Result<Option<String>, &'static str> {
    let has_client = optional_text(item, "client_id")?.is_some_and(|c| !c.trim().is_empty());
    if !has_client {
        return Ok(None);
    }
    let text = blocks_text(&item["content"], "text")?;
    Ok(Some(without_envelopes(&text).into_owned()))
}

fn agent_text(item: &Value) -> Result<Option<String>, &'static str> {
    if optional_text(item, "phase")? != Some("final_answer") {
        return Ok(None);
    }
    if !matches!(optional_text(item, "delivery")?, None | Some("sync")) {
        return Ok(None);
    }
    blocks_text(&item["content"], "Text").map(Some)
}

/// Art eines Tags an einer Textstelle.
enum Tag {
    /// Öffnender Hüllentag mit Namen und Länge; ohne `>` ist er unvollständig (`None`).
    Open(&'static str, Option<usize>),
    Close(&'static str, usize),
}

/// Erkennt einen Hüllentag am Anfang von `rest`. Nach dem Namen muss `>` oder ein Leerraum
/// folgen, damit `<app-contextual>` kein Treffer ist.
fn envelope_tag(rest: &str) -> Option<Tag> {
    for name in APP_ENVELOPES {
        if let Some(after) = rest
            .strip_prefix("</")
            .and_then(|r| r.strip_prefix(name))
            .and_then(|r| r.strip_prefix('>'))
        {
            return Some(Tag::Close(name, rest.len() - after.len()));
        }
        let Some(after) = rest.strip_prefix('<').and_then(|r| r.strip_prefix(name)) else {
            continue;
        };
        if after.starts_with('>') || after.starts_with(char::is_whitespace) {
            let length = after
                .find('>')
                .map(|end| rest.len() - after.len() + end + 1);
            return Some(Tag::Open(name, length));
        }
    }
    None
}

/// Entfernt Hüllen samt allen Teilinhalten und trimmt dann den Rand; ohne Hülle bleibt der
/// Text exakt. Verschachtelung zählt je Tagname: Erst der zum äußeren Tag passende schließende
/// Tag beendet den Block. Bleibt ein Block offen oder ist sein Tag unvollständig, fällt alles
/// ab diesem Tag weg. Ein schließender Tag ohne Anfang bleibt Text.
fn without_envelopes(text: &str) -> Cow<'_, str> {
    let mut kept = String::new();
    let mut copied_to = 0;
    let mut outer: Option<(&str, usize)> = None;
    let mut skip_to = 0;
    let mut changed = false;
    for (at, _) in text.match_indices('<') {
        if at < skip_to {
            continue;
        }
        let Some(tag) = envelope_tag(&text[at..]) else {
            continue;
        };
        match (tag, &mut outer) {
            (Tag::Open(_, None), _) => {
                // Unvollständiger Tag: nichts dahinter ist sicher Nutzertext.
                if outer.is_none() {
                    kept.push_str(&text[copied_to..at]);
                }
                return Cow::Owned(kept.trim().to_owned());
            }
            (Tag::Open(name, Some(length)), None) => {
                kept.push_str(&text[copied_to..at]);
                outer = Some((name, 1));
                changed = true;
                skip_to = at + length;
            }
            (Tag::Open(name, Some(length)), Some((outer_name, depth))) => {
                if name == *outer_name {
                    *depth += 1;
                }
                skip_to = at + length;
            }
            (Tag::Close(name, length), Some((outer_name, depth))) if name == *outer_name => {
                *depth -= 1;
                skip_to = at + length;
                if *depth == 0 {
                    outer = None;
                    copied_to = at + length;
                }
            }
            (Tag::Close(..), _) => {}
        }
    }
    if outer.is_some() {
        return Cow::Owned(kept.trim().to_owned());
    }
    if !changed {
        return Cow::Borrowed(text);
    }
    kept.push_str(&text[copied_to..]);
    Cow::Owned(kept.trim().to_owned())
}
