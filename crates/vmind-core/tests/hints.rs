use vmind_core::MemoryStore;

fn add(s: &MemoryStore, scope: &str, problem: &str) -> i64 {
    s.remember_scoped(scope, "error_solution", problem, "Lösung", "Test")
        .unwrap()
}
fn validated(s: &MemoryStore, scope: &str, problem: &str) -> i64 {
    let id = add(s, scope, problem);
    s.validate(id, "Prüfer", "Test").unwrap();
    id
}
fn ids(records: Vec<vmind_core::Record>) -> Vec<(i64, String)> {
    records.into_iter().map(|r| (r.id, r.status)).collect()
}

#[test]
fn pending_hints_follow_all_validated_hits_and_keep_their_order() {
    let s = MemoryStore::in_memory().unwrap();
    let hinweis = add(&s, "p", "Zertifikat abgelaufen im Proxy");
    let wort = validated(&s, "p", "Zertifikat abgelaufen");
    let teilwort = validated(&s, "global", "Serverzertifikat erneuern");
    let alt = s.recall("Zertifikat", "p", 5).unwrap();
    let neu = s.recall_with_hints("Zertifikat", "p", 5).unwrap();
    let validiert: Vec<i64> = alt.iter().map(|r| r.id).collect();
    assert_eq!(
        validiert,
        [wort, teilwort],
        "validierte Rangfolge wie bisher"
    );
    assert_eq!(
        ids(neu),
        [
            (wort, "validated".into()),
            (teilwort, "validated".into()),
            (hinweis, "pending".into())
        ]
    );
}

#[test]
fn pending_hints_only_fill_free_places_without_duplicates() {
    let s = MemoryStore::in_memory().unwrap();
    let a = validated(&s, "p", "Migration fehlt");
    let b = validated(&s, "p", "Migration bricht ab");
    add(&s, "p", "Migration hängt");
    let zwei = s.recall_with_hints("Migration", "p", 2).unwrap();
    assert_eq!(
        ids(zwei),
        [(a, "validated".into()), (b, "validated".into())]
    );
    let alle = s.recall_with_hints("Migration", "p", 20).unwrap();
    assert_eq!(alle.len(), 3);
    let mut gesehen: Vec<i64> = alle.iter().map(|r| r.id).collect();
    gesehen.dedup();
    assert_eq!(gesehen.len(), 3);
}

#[test]
fn pending_hints_keep_scope_and_withdrawal_filters() {
    let s = MemoryStore::in_memory().unwrap();
    let sichtbar = add(&s, "p", "Sperre beim Schreiben");
    let global = add(&s, "global", "Sperre beim Lesen");
    add(&s, "anderes", "Sperre im anderen Projekt");
    let zurueck = add(&s, "p", "Sperre falsch beschrieben");
    s.invalidate(zurueck, "Prüfer", "falsch").unwrap();
    let mut found: Vec<i64> = s
        .recall_with_hints("Sperre", "p", 20)
        .unwrap()
        .into_iter()
        .map(|r| r.id)
        .collect();
    found.sort();
    assert_eq!(found, [sichtbar, global]);
}

#[test]
fn pending_hints_use_partial_and_word_form_stages() {
    let s = MemoryStore::in_memory().unwrap();
    let teil = add(&s, "p", "Schemamigrationen scheitern");
    let form = add(&s, "p", "Zertifikat abgelaufen");
    assert!(
        s.recall_with_hints("Migration", "p", 5)
            .unwrap()
            .iter()
            .any(|r| r.id == teil)
    );
    assert!(
        s.recall_with_hints("Zertifikate", "p", 5)
            .unwrap()
            .iter()
            .any(|r| r.id == form)
    );
}

#[test]
fn validated_only_recall_never_returns_pending_entries() {
    let s = MemoryStore::in_memory().unwrap();
    add(&s, "p", "Nur ein Vorschlag");
    assert!(s.recall("Vorschlag", "p", 5).unwrap().is_empty());
    assert_eq!(s.recall_with_hints("Vorschlag", "p", 5).unwrap().len(), 1);
}

#[test]
fn recall_with_hints_validates_input_like_recall() {
    let s = MemoryStore::in_memory().unwrap();
    assert!(s.recall_with_hints("x", "p", 0).is_err());
    assert!(s.recall_with_hints("x", "p", 21).is_err());
    assert!(s.recall_with_hints("x", " ", 5).is_err());
    assert!(s.recall_with_hints(&"x".repeat(2001), "p", 5).is_err());
}
