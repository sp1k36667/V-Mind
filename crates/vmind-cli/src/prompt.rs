// Gemeinsame Startanweisung für externe KI-Clients und den lokalen Ollama-Adapter.
pub const START_PROMPT: &str = include_str!("../../../prompts/start.de.md");
/// Inhaltsgleiche englische Fassung; der Ollama-Adapter bleibt bei der deutschen.
pub const START_PROMPT_EN: &str = include_str!("../../../prompts/start.en.md");

/// Startanweisung in der gewünschten Sprache; ohne Angabe Deutsch (rückwärtskompatibel).
pub fn start_prompt(language: Option<&str>) -> Option<(&'static str, &'static str)> {
    match language {
        None | Some("de") => Some(("de", START_PROMPT)),
        Some("en") => Some(("en", START_PROMPT_EN)),
        Some(_) => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_is_german_and_english_is_available() {
        assert_eq!(start_prompt(None).unwrap().0, "de");
        assert!(
            start_prompt(Some("en"))
                .unwrap()
                .1
                .starts_with("# V-Mind: start")
        );
        assert!(start_prompt(Some("fr")).is_none());
    }

    #[test]
    fn both_languages_have_the_same_sections_and_operations() {
        let heading_count = |text: &str| text.lines().filter(|l| l.starts_with("## ")).count();
        assert_eq!(heading_count(START_PROMPT), heading_count(START_PROMPT_EN));
        // Jede Operation und jeder Prüfzustand muss in beiden Fassungen genannt sein.
        for name in [
            "`describe`",
            "`resume`",
            "`journal`",
            "`log`",
            "`recall`",
            "`get`",
            "`propose`",
            "`pending`",
            "`stats`",
            "`session_new`",
            "`sessions`",
            "`message`",
            "`messages`",
            "`check-set",
            "`revalidate",
            "`none`",
            "`not_run`",
            "`failed`",
            "`error`",
            "`passed`",
            "`last_verdict`",
            "context_only",
        ] {
            assert!(START_PROMPT.contains(name), "de fehlt {name}");
            assert!(START_PROMPT_EN.contains(name), "en fehlt {name}");
        }
    }
}
