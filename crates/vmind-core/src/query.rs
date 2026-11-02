//! Aufbereitung von Suchtexten: Suchwörter, Wortstämme für die Teilwortsuche und eine
//! Mindestabdeckung gegen Beifang. Reine Textfunktionen ohne Datenbankzugriff.
use crate::Record;

/// Funktionswörter zählen nicht als Suchwort. Eine Wortsuche kann Verneinung nicht
/// auswerten; „nicht“/„not“ würden nur beliebige Einträge treffen.
const STOP_WORDS: &[&str] = &[
    // Deutsch
    "der", "die", "das", "ein", "eine", "einer", "einem", "einen", "und", "oder", "ist", "sind",
    "mit", "für", "von", "zu", "im", "in", "am", "an", "wie", "was", "ich", "wir", "beim", "den",
    "dem", "des", "es", "nicht", "kein", "keine", "keinen", "nach", "vor", "ohne", "bei", "auf",
    "aus", "bis", "durch", "über", "unter", "um", "sich", "nur", "auch", "noch", "schon", "sehr",
    "wird", "werden", "wurde", "hat", "haben", "kann", "muss", "soll", "mein", "meine", "sein",
    "seine", "ihr", "er", "sie", "man", "dass", "wenn", "als", "so", "aber", "mal", "je", "zum",
    "zur", "vom", "warum", "wo", "dann", "da", "hier", "alle", "alles", "immer", "mehr",
    // Englisch
    "the", "a", "and", "or", "is", "to", "of", "how", "on", "for", "with", "by", "not", "no", "at",
    "it", "be", "was", "but", "from", "this", "that", "are", "as", "my", "i", "why", "what",
    "when",
];

/// Höchstens eine dieser Endungen wird abgetrennt, die längste zuerst.
const SUFFIXES: &[&str] = &["ern", "en", "er", "es", "e", "n", "s"];
const MIN_STEM_INPUT_CHARS: usize = 5;
const MIN_STEM_CHARS: usize = 4;
/// Der Trigramm-Index braucht mindestens drei Zeichen je Begriff.
const MIN_PARTIAL_TERM_CHARS: usize = 3;
const MAX_TERMS: usize = 24;

/// Suchbegriffe ohne Funktionswörter, klein geschrieben, ohne Dubletten, höchstens 24.
pub(crate) fn search_terms(query: &str) -> Vec<String> {
    let mut terms = Vec::new();
    for term in query
        .split(|c: char| !c.is_alphanumeric())
        .filter(|s| !s.is_empty())
    {
        let term = term.to_lowercase();
        if !STOP_WORDS.contains(&term.as_str()) && !terms.contains(&term) {
            terms.push(term);
        }
        if terms.len() == MAX_TERMS {
            break;
        }
    }
    terms
}

/// Einfacher Stamm: „Rundungsfehlern“ → „rundungsfehl“, „Zertifikate“ → „zertifikat“.
/// Der Stamm ist immer ein Anfang des Worts; Umlaut-Plurale („Passwörter“) und
/// unregelmäßige Formen („Indizes“) erkennt er nicht.
pub(crate) fn stem(term: &str) -> &str {
    let chars = term.chars().count();
    if chars < MIN_STEM_INPUT_CHARS {
        return term;
    }
    SUFFIXES
        .iter()
        .find(|s| term.ends_with(*s) && chars - s.chars().count() >= MIN_STEM_CHARS)
        .map_or(term, |s| &term[..term.len() - s.len()])
}

/// Begriffe für die Teilwortsuche: Stämme, mindestens drei Zeichen, ohne Dubletten.
pub(crate) fn partial_terms(terms: &[String]) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    for stem in terms.iter().map(|t| stem(t)) {
        if stem.chars().count() >= MIN_PARTIAL_TERM_CHARS && !out.iter().any(|o| o == stem) {
            out.push(stem.to_string());
        }
    }
    out
}

// Nur gequotete Begriffe gelangen in MATCH, keine vom Aufrufer gelieferte FTS-Syntax.
pub(crate) fn match_expression<'a>(terms: impl Iterator<Item = &'a String>) -> String {
    terms
        .map(|t| format!("\"{t}\""))
        .collect::<Vec<_>>()
        .join(" OR ")
}

/// Kleinschreibung und Umlaute ohne Punkte, wie bei der Wortsuche (remove_diacritics).
fn fold(text: &str) -> String {
    text.to_lowercase()
        .chars()
        .map(|c| match c {
            'ä' => 'a',
            'ö' => 'o',
            'ü' => 'u',
            other => other,
        })
        .collect()
}

/// Wie viele Suchwörter (über ihren Stamm) im Eintrag vorkommen.
fn coverage(record: &Record, stems: &[String]) -> usize {
    let text = fold(&format!("{} {}", record.problem, record.solution));
    stems.iter().filter(|s| text.contains(s.as_str())).count()
}

/// Behält nur Treffer, die mindestens halb so viele Suchwörter enthalten wie der beste,
/// in unveränderter Reihenfolge. Enthält kein Treffer ein Suchwort (etwa bei einer
/// abweichenden Schreibweise), bleibt die Liste unverändert.
pub(crate) fn keep_covering(records: Vec<Record>, terms: &[String]) -> Vec<Record> {
    let stems: Vec<String> = terms.iter().map(|t| fold(stem(t))).collect();
    let counts: Vec<usize> = records.iter().map(|r| coverage(r, &stems)).collect();
    let best = counts.iter().copied().max().unwrap_or(0);
    if best == 0 {
        return records;
    }
    let need = best.div_ceil(2);
    records
        .into_iter()
        .zip(counts)
        .filter(|(_, c)| *c >= need)
        .map(|(r, _)| r)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stems_cut_one_common_ending_and_keep_short_words() {
        assert_eq!(stem("rundungsfehlern"), "rundungsfehl");
        assert_eq!(stem("zertifikate"), "zertifikat");
        assert_eq!(stem("cronjobs"), "cronjob");
        assert_eq!(stem("lesern"), "leser");
        assert_eq!(stem("files"), "file");
        assert_eq!(stem("kosten"), "kost");
        assert_eq!(stem("ollama"), "ollama");
        assert_eq!(stem("port"), "port");
        assert_eq!(stem("passwörter"), "passwört");
    }

    #[test]
    fn negation_and_function_words_are_not_search_terms() {
        assert_eq!(search_terms("Dienst startet nicht"), ["dienst", "startet"]);
        assert_eq!(
            search_terms("No such file or directory"),
            ["such", "file", "directory"]
        );
        assert!(search_terms("nicht vor ohne").is_empty());
    }

    #[test]
    fn partial_terms_are_unique_stems_of_at_least_three_chars() {
        let terms = vec![
            "druckern".into(),
            "drucker".into(),
            "ab".into(),
            "port".into(),
        ];
        assert_eq!(partial_terms(&terms), ["druck", "port"]);
    }
}
