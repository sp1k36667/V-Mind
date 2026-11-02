use vmind_core::MemoryStore;

fn validated(s: &MemoryStore, scope: &str, problem: &str) -> i64 {
    let id = s
        .remember_scoped(scope, "error_solution", problem, "Lösung", "Test")
        .unwrap();
    s.validate(id, "Prüfer", "Test bestanden").unwrap();
    id
}

#[test]
fn finds_inflected_and_compound_german_words() {
    let s = MemoryStore::in_memory().unwrap();
    let compound = validated(&s, "global", "Schemamigrationen schlagen beim Start fehl");
    let ids: Vec<i64> = s
        .recall("Migration", "global", 5)
        .unwrap()
        .iter()
        .map(|r| r.id)
        .collect();
    assert_eq!(ids, [compound]);
}

#[test]
fn whole_word_matches_rank_before_partial_matches() {
    let s = MemoryStore::in_memory().unwrap();
    let partial = validated(&s, "global", "Datenbankmigrationen brechen ab");
    let word = validated(&s, "global", "Migration bricht ab");
    let ids: Vec<i64> = s
        .recall("Migration", "global", 5)
        .unwrap()
        .iter()
        .map(|r| r.id)
        .collect();
    assert_eq!(ids, [word, partial]);
    assert_eq!(s.recall("Migration", "global", 1).unwrap()[0].id, word);
}

#[test]
fn partial_matches_keep_status_and_scope_filters() {
    let s = MemoryStore::in_memory().unwrap();
    s.remember_scoped("p", "long_term", "Ungeprüfte Schemamigration", "x", "Test")
        .unwrap();
    let withdrawn = validated(&s, "p", "Zurückgezogene Schemamigration");
    s.invalidate(withdrawn, "Prüfer", "veraltet").unwrap();
    validated(&s, "anderes", "Fremde Schemamigration");
    let global = validated(&s, "global", "Globale Schemamigration");
    let own = validated(&s, "p", "Eigene Schemamigration");
    let mut ids: Vec<i64> = s
        .recall("Migration", "p", 20)
        .unwrap()
        .iter()
        .map(|r| r.id)
        .collect();
    ids.sort();
    assert_eq!(ids, [global, own]);
}

#[test]
fn short_terms_and_fts_syntax_do_not_break_partial_search() {
    let s = MemoryStore::in_memory().unwrap();
    validated(&s, "global", "Schemamigration");
    assert!(s.recall("DB", "global", 5).unwrap().is_empty());
    assert!(
        s.recall("\" OR * NOT : ()", "global", 5)
            .unwrap()
            .is_empty()
    );
    assert_eq!(s.recall("igr", "global", 5).unwrap().len(), 1);
}

#[test]
fn longer_inflected_query_forms_find_the_shorter_stored_word() {
    let s = MemoryStore::in_memory().unwrap();
    let money = validated(&s, "global", "Rundungsfehler bei Geldbeträgen");
    let cert = validated(&s, "global", "TLS-Zertifikat ist abgelaufen");
    assert_eq!(
        s.recall("Rundungsfehlern", "global", 5).unwrap()[0].id,
        money
    );
    assert_eq!(
        s.recall("abgelaufene Zertifikate", "global", 5).unwrap()[0].id,
        cert
    );
    // Umlaut-Plurale bleiben eine bekannte Grenze des einfachen Stamms.
    validated(&s, "global", "Passwort ist zu kurz");
    assert!(s.recall("Passwörter", "global", 5).unwrap().is_empty());
}

#[test]
fn negation_alone_finds_nothing_and_weakly_covered_hits_are_dropped() {
    let s = MemoryStore::in_memory().unwrap();
    validated(&s, "global", "Drucker druckt nicht");
    let service = validated(&s, "global", "Dienst startet nach dem Neustart nicht");
    let other = validated(&s, "global", "Dienst meldet Fehler");
    assert!(s.recall("nicht", "global", 5).unwrap().is_empty());
    // Der beste Treffer enthält beide Suchwörter; einer mit nur einem von zwei bleibt.
    let ids: Vec<i64> = s
        .recall("Dienst startet nicht", "global", 5)
        .unwrap()
        .iter()
        .map(|r| r.id)
        .collect();
    assert_eq!(ids, [service, other]);
    // Bei vier Suchwörtern braucht ein Treffer mindestens zwei davon.
    let ids: Vec<i64> = s
        .recall("Dienst startet Neustart automatisch", "global", 5)
        .unwrap()
        .iter()
        .map(|r| r.id)
        .collect();
    assert_eq!(ids, [service]);
}

#[test]
fn partial_index_follows_updates_after_withdrawal() {
    let s = MemoryStore::in_memory().unwrap();
    let id = validated(&s, "global", "Schemamigration");
    s.invalidate(id, "Prüfer", "falsch").unwrap();
    assert!(s.recall("Migration", "global", 5).unwrap().is_empty());
    assert_eq!(s.stats("global").unwrap().schema_version, 6);
}
