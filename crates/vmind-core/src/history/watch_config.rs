//! Konfiguration des automatischen Codex-Imports (`history.json`). Ohne Datei liest V-Mind
//! keine Quelle. Alle Pfade sind absolut; Arbeitsordner werden komponentenweise einem Bereich
//! zugeordnet, das längste passende Präfix gewinnt, und es gibt keinen Ausweichbereich.
use super::check_scope;
use serde::Deserialize;
use std::{
    collections::BTreeMap,
    path::{Component, Path, PathBuf},
};

const DEFAULT_DAYS: u32 = 7;
const MAX_DAYS: u32 = 366;
const MAX_RULES: usize = 1000;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawConfig {
    database: PathBuf,
    codex_sessions: Option<PathBuf>,
    days: Option<u32>,
    scopes: Vec<RawRule>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawRule {
    cwd: PathBuf,
    scope: String,
}

/// Geprüfte Konfiguration; nur über `parse` erzeugbar.
#[derive(Debug, Clone)]
pub struct WatchConfig {
    database: PathBuf,
    codex_sessions: PathBuf,
    days: u32,
    /// Normalisierter Arbeitsordner → Bereich; eindeutig je Pfad.
    rules: BTreeMap<PathBuf, String>,
}

/// Absoluter Pfad ohne `..`, mit entfernten `.`-Teilen und Schrägstrichen am Ende.
pub(super) fn normalized(path: &Path) -> Option<PathBuf> {
    if !path.is_absolute() || path.components().any(|c| c == Component::ParentDir) {
        return None;
    }
    Some(path.components().collect())
}

fn absolute(path: &Path, what: &str) -> Result<PathBuf, String> {
    normalized(path).ok_or_else(|| format!("{what} muss ein absoluter Pfad ohne „..“ sein"))
}

impl WatchConfig {
    /// Liest JSON; `home` liefert den Standard `HOME/.codex/sessions`, wenn die Wurzel fehlt.
    pub fn parse(text: &str, home: Option<&Path>) -> Result<Self, String> {
        let raw: RawConfig =
            serde_json::from_str(text).map_err(|e| format!("Konfiguration ungültig: {e}"))?;
        let database = absolute(&raw.database, "database")?;
        let codex_sessions = match (&raw.codex_sessions, home) {
            (Some(root), _) => absolute(root, "codex_sessions")?,
            (None, Some(home)) => absolute(&home.join(".codex/sessions"), "HOME")?,
            (None, None) => {
                return Err("codex_sessions fehlt und HOME ist nicht gesetzt".into());
            }
        };
        let days = raw.days.unwrap_or(DEFAULT_DAYS);
        if !(1..=MAX_DAYS).contains(&days) {
            return Err(format!("days muss 1 bis {MAX_DAYS} sein"));
        }
        if raw.scopes.is_empty() || raw.scopes.len() > MAX_RULES {
            return Err(format!("scopes braucht 1 bis {MAX_RULES} Zuordnungen"));
        }
        let mut rules = BTreeMap::new();
        for rule in raw.scopes {
            let cwd = absolute(&rule.cwd, "cwd")?;
            check_scope(&rule.scope)
                .map_err(|_| format!("Ungültiger Bereich für {}", cwd.display()))?;
            match rules.get(&cwd) {
                Some(known) if *known != rule.scope => {
                    return Err(format!(
                        "Mehrdeutige Zuordnung: {} gehört zu {known} und {}",
                        cwd.display(),
                        rule.scope
                    ));
                }
                Some(_) => {}
                None => {
                    rules.insert(cwd, rule.scope);
                }
            }
        }
        Ok(Self {
            database,
            codex_sessions,
            days,
            rules,
        })
    }

    pub fn database(&self) -> &Path {
        &self.database
    }

    pub fn codex_sessions(&self) -> &Path {
        &self.codex_sessions
    }

    pub fn days(&self) -> u32 {
        self.days
    }

    /// Bereich des längsten passenden Präfixes. `Path::starts_with` vergleicht Komponenten,
    /// daher gehört `/a/project-extra` nicht zu `/a/project`. Gleich lange passende Präfixe
    /// sind derselbe Pfad und wurden beim Laden auf einen Bereich festgelegt.
    pub fn scope_for(&self, cwd: &Path) -> Option<&str> {
        let cwd = normalized(cwd)?;
        self.rules
            .iter()
            .filter(|(prefix, _)| cwd.starts_with(prefix))
            .max_by_key(|(prefix, _)| prefix.components().count())
            .map(|(_, scope)| scope.as_str())
    }
}
