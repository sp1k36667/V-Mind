use std::sync::{Arc, Barrier};
use std::thread;
use vmind_core::{CheckResult, MemoryStore, Outcome};

fn result(outcome: Outcome) -> CheckResult {
    CheckResult {
        outcome,
        exit_code: Some(if outcome == Outcome::Passed { 0 } else { 1 }),
        duration_ms: 12,
        output: "geheime Ausgabe 1 failed".into(),
    }
}
/// Eintrag im Bereich mit gesetztem Prüfbefehl; gibt Eintrag und Prüfbefehl zurück.
fn entry_with_check(store: &MemoryStore, scope: &str) -> (i64, vmind_core::Check) {
    let id = store
        .remember_scoped(
            scope,
            "error_solution",
            "JSON kaputt",
            "Atomar schreiben",
            "T",
        )
        .unwrap();
    store
        .set_check(id, &["cargo".into(), "test".into()], "/w", "tester")
        .unwrap();
    (id, store.active_check(id).unwrap().unwrap())
}
fn runs(store: &MemoryStore, check: &vmind_core::Check, outcomes: &[Outcome]) -> Vec<i64> {
    outcomes
        .iter()
        .map(|o| store.apply_check(check, &result(*o), false).unwrap().run_id)
        .collect()
}

#[test]
fn lists_only_direct_failed_to_passed_transitions() {
    use Outcome::*;
    let s = MemoryStore::in_memory().unwrap();
    let (memory, check) = entry_with_check(&s, "p");
    let r = runs(&s, &check, &[Failed, Passed, Failed, Error, Passed, Passed]);
    let found = s.repairs("p").unwrap();
    assert_eq!(found.len(), 1, "error unterbricht den Übergang");
    assert_eq!(
        (
            found[0].memory_id,
            found[0].check_id,
            found[0].failed_run,
            found[0].passed_run
        ),
        (memory, check.id, r[0], r[1])
    );
    assert_eq!(
        (found[0].failed_exit, found[0].passed_exit),
        (Some(1), Some(0))
    );
}

#[test]
fn repairs_keep_scope_withdrawal_and_active_check_limits() {
    use Outcome::*;
    let s = MemoryStore::in_memory().unwrap();
    let (_, global) = entry_with_check(&s, "global");
    let (_, fremd) = entry_with_check(&s, "anderes");
    let (zurueck, zurueck_check) = entry_with_check(&s, "p");
    let (ersetzt, ersetzt_check) = entry_with_check(&s, "p");
    for c in [&global, &fremd, &zurueck_check, &ersetzt_check] {
        runs(&s, c, &[Failed, Passed]);
    }
    s.invalidate(zurueck, "tester", "falsch").unwrap();
    s.set_check(ersetzt, &["neu".into()], "/w", "tester")
        .unwrap();
    let found: Vec<i64> = s.repairs("p").unwrap().iter().map(|r| r.check_id).collect();
    assert_eq!(
        found,
        [global.id],
        "nur sichtbar, nicht zurückgezogen, aktiver Check"
    );
    let fremd_lauf = s.check_runs(fremd.memory_id, 2).unwrap()[1].id;
    assert!(s.propose_repair("p", fremd_lauf, "P", "L").is_err());
}

#[test]
fn proposal_is_pending_with_canonical_source_and_caller_text_only() {
    use Outcome::*;
    let s = MemoryStore::in_memory().unwrap();
    let (memory, check) = entry_with_check(&s, "p");
    let r = runs(&s, &check, &[Failed, Passed]);
    let id = s
        .propose_repair("p", r[0], "Speichern bricht ab", "Temp-Datei umbenennen")
        .unwrap();
    let record = s.get(id).unwrap().unwrap();
    assert_eq!(record.status, "pending");
    assert_eq!(record.scope, "p");
    assert_eq!(record.problem, "Speichern bricht ab");
    assert_eq!(record.solution, "Temp-Datei umbenennen");
    assert_eq!(
        record.source,
        format!(
            "Reparatur: Prüfbefehl #{} an Eintrag #{memory}, Lauf #{} fehlgeschlagen → Lauf #{} bestanden",
            check.id, r[0], r[1]
        )
    );
    assert!(!record.source.contains("cargo") && !record.source.contains("geheim"));
}

#[test]
fn proposal_rejects_non_transitions_duplicates_and_blank_text() {
    use Outcome::*;
    let s = MemoryStore::in_memory().unwrap();
    let (_, check) = entry_with_check(&s, "p");
    let r = runs(&s, &check, &[Failed, Error, Passed, Failed, Passed]);
    assert!(
        s.propose_repair("p", r[0], "P", "L").is_err(),
        "error dazwischen"
    );
    assert!(
        s.propose_repair("p", r[2], "P", "L").is_err(),
        "bestandener Lauf"
    );
    assert!(
        s.propose_repair("p", 9999, "P", "L").is_err(),
        "unbekannter Lauf"
    );
    assert!(
        s.propose_repair("p", r[3], " ", "L").is_err(),
        "leeres Problem"
    );
    s.propose_repair("p", r[3], "P", "L").unwrap();
    assert!(s.propose_repair("p", r[3], "P2", "L2").is_err(), "doppelt");
    assert_eq!(s.pending("p").unwrap().len(), 1, "nur ein Vorschlag");
}

#[test]
fn concurrent_proposals_for_the_same_pair_store_one_entry() {
    use Outcome::*;
    let dir = std::env::temp_dir().join(format!("vmind-repair-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir(&dir).unwrap();
    let path = dir.join("v.db");
    let s = MemoryStore::open(&path).unwrap();
    let (_, check) = entry_with_check(&s, "p");
    let failed = runs(&s, &check, &[Failed, Passed])[0];
    let barrier = Arc::new(Barrier::new(8));
    let handles: Vec<_> = (0..8)
        .map(|_| {
            let (path, barrier) = (path.clone(), barrier.clone());
            thread::spawn(move || {
                let store = MemoryStore::open(&path).unwrap();
                barrier.wait();
                store.propose_repair("p", failed, "P", "L").is_ok()
            })
        })
        .collect();
    let ok = handles
        .into_iter()
        .map(|h| h.join().unwrap())
        .filter(|ok| *ok)
        .count();
    assert_eq!(ok, 1, "genau ein Aufruf erfolgreich");
    assert_eq!(s.pending("p").unwrap().len(), 1, "genau ein Vorschlag");
    drop(s);
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn proposals_for_a_global_check_stay_in_each_callers_scope() {
    use Outcome::*;
    let s = MemoryStore::in_memory().unwrap();
    let (_, check) = entry_with_check(&s, "global");
    let failed = runs(&s, &check, &[Failed, Passed])[0];
    let a = s.propose_repair("a", failed, "Text A", "Lösung A").unwrap();
    let b = s.propose_repair("b", failed, "Text B", "Lösung B").unwrap();
    assert_eq!(s.get(a).unwrap().unwrap().scope, "a");
    assert_eq!(s.get(b).unwrap().unwrap().scope, "b");
    let error = s
        .propose_repair("a", failed, "P", "L")
        .unwrap_err()
        .to_string();
    assert!(!error.contains("Text B") && !error.contains(&b.to_string()));
    let shown = |scope| -> Vec<String> {
        s.pending(scope)
            .unwrap()
            .into_iter()
            .map(|r| r.problem)
            .collect()
    };
    assert_eq!(shown("a"), ["Text A"], "Projekt b bleibt unsichtbar");
    assert_eq!(shown("b"), ["Text B"]);
    assert!(
        shown("global").is_empty(),
        "nichts global ohne Aufruf in global"
    );
    let g = s.propose_repair("global", failed, "Global", "L").unwrap();
    assert_eq!(s.get(g).unwrap().unwrap().scope, "global");
}
