//! `vmind observe DB`: liest eine Claude-Code-Hook-Meldung (PostToolUse oder
//! PostToolUseFailure) von stdin und speichert nur Sitzung, Aufruf-ID, Werkzeug,
//! Ergebnis und betroffene Projektdatei. Befehle, Ausgaben, Fehlertexte und
//! Dateiinhalte werden nicht ausgewertet und nicht gespeichert; nichts wird ausgeführt.
use serde_json::Value;
use std::{
    io::{self, Read},
    path::{Component, Path},
};
use vmind_core::{MemoryStore, Observation};

/// Hook-Meldungen enthalten bei Write den ganzen Dateiinhalt; darüber wird abgelehnt.
const MAX_INPUT_BYTES: u64 = 16 * 1024 * 1024;
const TOOLS: [&str; 3] = ["Bash", "Edit", "Write"];

fn field<'a>(input: &'a Value, name: &str) -> crate::Result<&'a str> {
    input[name]
        .as_str()
        .ok_or_else(|| io::Error::other(format!("Hook-Meldung ohne Feld {name}")).into())
}

/// Projektdatei relativ zum Projektordner; Dateien außerhalb werden nicht genannt.
fn project_path(file: &str, root: &Path) -> Option<String> {
    let file = Path::new(file);
    if !root.is_absolute()
        || !file.is_absolute()
        || root.components().any(|c| matches!(c, Component::ParentDir))
    {
        return None;
    }
    let relative = file.strip_prefix(root).ok()?;
    let mut parts = Vec::new();
    for component in relative.components() {
        match component {
            Component::Normal(value) => parts.push(value.to_str()?),
            _ => return None,
        }
    }
    (!parts.is_empty()).then(|| parts.join("/"))
}

/// `None`, wenn die Meldung kein unterstütztes Werkzeug betrifft (wird still ignoriert).
pub fn observation(input: &Value, root: &Path) -> crate::Result<Option<Observation>> {
    let result = match field(input, "hook_event_name")? {
        "PostToolUse" => "completed",
        "PostToolUseFailure" => "failed",
        _ => {
            return Err(io::Error::other("Hook-Ereignis wird nicht unterstützt").into());
        }
    };
    let tool = field(input, "tool_name")?;
    if !TOOLS.contains(&tool) {
        return Ok(None);
    }
    let paths = match tool {
        // Nur der Pfad; old_string, new_string und content bleiben unberührt.
        "Edit" | "Write" => input["tool_input"]["file_path"]
            .as_str()
            .and_then(|f| project_path(f, root))
            .into_iter()
            .collect(),
        _ => Vec::new(),
    };
    Ok(Some(Observation {
        session_id: field(input, "session_id")?.into(),
        tool_use_id: field(input, "tool_use_id")?.into(),
        tool: tool.into(),
        result: result.into(),
        paths,
    }))
}

pub fn run(db: &str, scope: &str) -> crate::Result<()> {
    let mut raw = Vec::new();
    io::stdin()
        .lock()
        .take(MAX_INPUT_BYTES + 1)
        .read_to_end(&mut raw)?;
    if raw.len() as u64 > MAX_INPUT_BYTES {
        return Err(io::Error::other("Hook-Meldung größer als 16 MiB, nicht gespeichert").into());
    }
    let input: Value = serde_json::from_slice(&raw)?;
    let root = std::env::var("CLAUDE_PROJECT_DIR")
        .ok()
        .or_else(|| input["cwd"].as_str().map(String::from))
        .ok_or_else(|| io::Error::other("Projektordner unbekannt (CLAUDE_PROJECT_DIR oder cwd)"))?;
    let root = Path::new(&root);
    if !root.is_absolute() || root.components().any(|c| matches!(c, Component::ParentDir)) {
        return Err(io::Error::other("Projektordner muss ein absoluter Pfad ohne .. sein").into());
    }
    if let Some(o) = observation(&input, root)? {
        // Kein Upgrade aus einem Hook heraus: nur aktuelles Schema, keine neue Datei.
        MemoryStore::open_current(db)?.observe(scope, &o)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn hook(event: &str, tool: &str, extra: Value) -> Value {
        let mut v = json!({"session_id": "s1", "tool_use_id": "toolu_1",
            "hook_event_name": event, "tool_name": tool, "cwd": "/projekt"});
        for (k, x) in extra.as_object().unwrap() {
            v[k] = x.clone();
        }
        v
    }

    #[test]
    fn write_keeps_only_the_relative_path_never_the_content() {
        let input = hook(
            "PostToolUse",
            "Write",
            json!({"tool_input": {"file_path": "/projekt/src/a.rs", "content": "GEHEIM"},
                   "tool_response": {"filePath": "/projekt/src/a.rs"}}),
        );
        let o = observation(&input, Path::new("/projekt")).unwrap().unwrap();
        assert_eq!((o.tool.as_str(), o.result.as_str()), ("Write", "completed"));
        assert_eq!(o.paths, ["src/a.rs"]);
        assert!(!format!("{o:?}").contains("GEHEIM"));
    }

    #[test]
    fn failures_and_bash_store_no_command_error_or_outside_paths() {
        let bash = hook(
            "PostToolUseFailure",
            "Bash",
            json!({"tool_input": {"command": "curl -H 'token: X'"}, "error": "Exit code 1\nX"}),
        );
        let o = observation(&bash, Path::new("/projekt")).unwrap().unwrap();
        assert_eq!(o.result, "failed");
        assert!(o.paths.is_empty());
        assert!(!format!("{o:?}").contains("token"));
        let outside = hook(
            "PostToolUse",
            "Edit",
            json!({"tool_input": {"file_path": "/home/u/.ssh/config"}}),
        );
        let o = observation(&outside, Path::new("/projekt"))
            .unwrap()
            .unwrap();
        assert!(o.paths.is_empty());
    }

    #[test]
    fn other_tools_are_ignored_and_broken_reports_rejected() {
        let read = hook("PostToolUse", "Read", json!({}));
        assert!(observation(&read, Path::new("/projekt")).unwrap().is_none());
        let pre = hook("PreToolUse", "Bash", json!({}));
        assert!(observation(&pre, Path::new("/projekt")).is_err());
        let mut no_id = hook("PostToolUse", "Bash", json!({}));
        no_id.as_object_mut().unwrap().remove("tool_use_id");
        assert!(observation(&no_id, Path::new("/projekt")).is_err());
    }
}

#[cfg(test)]
mod path_regressions {
    use super::*;

    #[test]
    fn traversal_and_empty_roots_do_not_disclose_external_paths() {
        assert!(project_path("/projekt/../secret/key", Path::new("/projekt")).is_none());
        assert!(project_path("/secret/key", Path::new("")).is_none());
        assert!(project_path("relative/file", Path::new("relative")).is_none());
        assert_eq!(
            project_path("/projekt/src/file.rs", Path::new("/projekt")),
            Some("src/file.rs".into())
        );
        assert_eq!(
            project_path("/projekt/./src/a.rs", Path::new("/projekt")),
            Some("src/a.rs".into())
        );
    }
}
