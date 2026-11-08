//! Lange Anfragen: Alle Begriffe zählen, die Zeichengrenze und die Filter bleiben bestehen.
use vmind_core::MemoryStore;

const MAX_QUERY_CHARS: usize = 2000;
/// Zweistellige Begriffe aus `search_terms`' Stoppwortliste; sie zählen nicht als Begriffe.
const TWO_LETTER_STOP_WORDS: &[&str] =
    &["zu", "im", "in", "am", "an", "es", "or", "is", "to", "of"];

fn add(s: &MemoryStore, scope: &str, problem: &str) -> i64 {
    s.remember_scoped(scope, "error_solution", problem, "Lösung", "Test")
        .unwrap()
}

fn validated(s: &MemoryStore, scope: &str, problem: &str) -> i64 {
    let id = add(s, scope, problem);
    s.validate(id, "Prüfer", "Test").unwrap();
    id
}

/// Verschiedene Füllwörter, die in keinem Testeintrag vorkommen.
fn fillers(count: usize) -> Vec<String> {
    (0..count).map(|i| format!("qxz{i:03}")).collect()
}

/// Anfrage aus `count` Füllwörtern, dahinter `last`.
fn query_with_last_term(count: usize, last: &str) -> String {
    let mut terms = fillers(count);
    terms.push(last.to_string());
    terms.join(" ")
}

fn ids(records: &[vmind_core::Record]) -> Vec<i64> {
    records.iter().map(|r| r.id).collect()
}

/// Alle zweistelligen Buchstabenkombinationen ohne Stoppwörter, in fester Reihenfolge.
fn two_letter_terms() -> Vec<String> {
    let letters = || 'a'..='z';
    letters()
        .flat_map(|first| letters().map(move |second| format!("{first}{second}")))
        .filter(|term| !TWO_LETTER_STOP_WORDS.contains(&term.as_str()))
        .collect()
}

#[test]
fn term_behind_position_24_finds_the_entry() {
    let s = MemoryStore::in_memory().unwrap();
    let eintrag = validated(&s, "p", "Zertifikat abgelaufen");

    let found = s
        .recall(&query_with_last_term(30, "zertifikat"), "p", 5)
        .unwrap();

    assert_eq!(ids(&found), [eintrag]);
}

#[test]
fn query_with_exactly_24_terms_finds_term_24_in_rule_order() {
    let s = MemoryStore::in_memory().unwrap();
    let erster = validated(&s, "p", "Druckerwarteschlange blockiert");
    let letzter = validated(&s, "p", "Zertifikat blockiert");
    validated(&s, "p", "Festplatte voll");
    let mut terms = vec!["druckerwarteschlange".to_string()];
    terms.extend(fillers(22));
    terms.push("zertifikat".to_string());
    assert_eq!(terms.len(), 24, "Vorbedingung: genau 24 Begriffe");

    let lang = s.recall(&terms.join(" "), "p", 5).unwrap();
    let kurz = s.recall("druckerwarteschlange zertifikat", "p", 5).unwrap();

    // Gleich lange Einträge mit je einem Treffer: BM25 gleich, danach entscheidet die ID.
    assert_eq!(ids(&lang), [erster, letzter]);
    assert_eq!(ids(&lang), ids(&kurz));
}

#[test]
fn filters_hold_when_the_matching_term_is_behind_position_24() {
    let s = MemoryStore::in_memory().unwrap();
    let hinweis = add(&s, "p", "Sperrdatei");
    let sichtbar = validated(&s, "p", "Sperrdatei bleibt nach dem Absturz liegen");
    validated(&s, "anderes", "Sperrdatei im fremden Bereich");
    let zurueck = validated(&s, "p", "Sperrdatei falsch beschrieben");
    s.invalidate(zurueck, "Prüfer", "falsch").unwrap();
    let anfrage = query_with_last_term(30, "sperrdatei");

    let nur_validiert = s.recall(&anfrage, "p", 20).unwrap();
    let mit_hinweisen = s.recall_with_hints(&anfrage, "p", 20).unwrap();

    assert_eq!(ids(&nur_validiert), [sichtbar]);
    assert_eq!(
        mit_hinweisen
            .iter()
            .map(|r| (r.id, r.status.as_str()))
            .collect::<Vec<_>>(),
        [(sichtbar, "validated"), (hinweis, "pending")],
        "ungeprüfter Eintrag nur als Hinweis und hinter validierten"
    );
}

#[test]
fn near_limit_query_with_many_distinct_short_terms_runs() {
    let s = MemoryStore::in_memory().unwrap();
    let terms: Vec<String> = two_letter_terms()
        .into_iter()
        .take(MAX_QUERY_CHARS.div_ceil(3))
        .collect();
    let anfrage = terms.join(" ");
    assert!(terms.len() >= 600, "nur {} Begriffe", terms.len());
    assert!(anfrage.chars().count() <= MAX_QUERY_CHARS);
    let letzter = terms.last().unwrap();
    let eintrag = validated(&s, "p", &format!("Fehlercode {letzter} tritt auf"));

    let found = s
        .recall(&anfrage, "p", 5)
        .expect("lange Anfrage mit vielen kurzen Begriffen");

    assert_eq!(ids(&found), [eintrag]);
}

/// Sechsstellige Begriffe durchlaufen ohne Treffer alle drei Suchstufen, auch Teilwort und Wortform.
#[test]
fn near_limit_query_runs_through_all_search_stages() {
    let s = MemoryStore::in_memory().unwrap();
    validated(&s, "p", "Festplatte voll");
    let terms = fillers((MAX_QUERY_CHARS + 1) / 7);
    let anfrage = terms.join(" ");
    assert!(terms.len() >= 250, "nur {} Begriffe", terms.len());
    assert!(anfrage.chars().count() <= MAX_QUERY_CHARS);

    let found = s
        .recall_with_hints(&anfrage, "p", 5)
        .expect("lange Anfrage über alle Suchstufen");

    assert!(found.is_empty());
}
