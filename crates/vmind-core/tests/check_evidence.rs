use serde_json::{Value, json};
use vmind_core::{Check, CheckResult, MemoryStore, Outcome};

fn record(s: &MemoryStore, id: i64) -> Value {
    serde_json::to_value(s.get(id).unwrap().unwrap()).unwrap()
}
fn run(s: &MemoryStore, check: &Check, outcome: Outcome) {
    s.apply_check(
        check,
        &CheckResult {
            outcome,
            exit_code: match outcome {
                Outcome::Passed => Some(0),
                Outcome::Failed => Some(1),
                Outcome::Error => None,
            },
            duration_ms: 1,
            output: "synthetischer Prüflauf".into(),
        },
        false,
    )
    .unwrap();
}
#[test]
fn evidence_tracks_the_active_definition_without_changing_validation_status() {
    let s = MemoryStore::in_memory().unwrap();
    let id = s
        .remember_scoped("p", "long_term", "Prüfzustand", "Lösung", "Test")
        .unwrap();
    assert_eq!(record(&s, id)["check"]["state"], "none");
    let first = s
        .set_check(id, &["test-command".into()], "/", "Tester")
        .unwrap();
    let check = s.active_check(id).unwrap().unwrap();
    assert_eq!(record(&s, id)["check"]["state"], "not_run");
    run(&s, &check, Outcome::Passed);
    let passed = record(&s, id);
    assert_eq!(passed["status"], "validated");
    assert_eq!(passed["check"]["state"], "passed");
    assert_eq!(passed["check"]["check_id"], first);
    let pass_id = passed["check"]["run_id"].clone();
    run(&s, &check, Outcome::Error);
    let error = record(&s, id);
    assert_eq!(error["status"], "validated");
    assert_eq!(error["check"]["state"], "error");
    assert_eq!(error["check"]["last_verdict"]["outcome"], "passed");
    assert_eq!(error["check"]["last_verdict"]["run_id"], pass_id);
    run(&s, &check, Outcome::Failed);
    let failed = record(&s, id);
    assert_eq!(failed["status"], "validated");
    assert_eq!(failed["check"]["state"], "failed");
    assert_eq!(failed["check"]["last_verdict"]["outcome"], "failed");
    run(&s, &check, Outcome::Error);
    let after_error = record(&s, id);
    assert_eq!(after_error["check"]["state"], "error");
    assert_eq!(after_error["check"]["last_verdict"]["outcome"], "failed");

    assert_eq!(
        s.recall("Prüfzustand", "p", 5).unwrap().len(),
        1,
        "report-only failure must not silently withdraw"
    );
    let second = s
        .set_check(id, &["replacement-command".into()], "/", "Tester")
        .unwrap();
    let replaced = record(&s, id);
    assert_eq!(replaced["status"], "validated");
    assert_eq!(
        replaced["check"],
        json!({"state":"not_run","check_id":second,"run_id":null,"run_at":null,"last_verdict":null})
    );
    assert_eq!(
        s.check_runs(id, 10).unwrap().len(),
        4,
        "old runs remain in history"
    );
}

#[test]
fn failed_pending_stays_pending_and_recall_shows_mixed_evidence() {
    let s = MemoryStore::in_memory().unwrap();
    let pending = s
        .remember_scoped(
            "p",
            "long_term",
            "Gemeinsamer Prüfbegriff",
            "ungeprüft",
            "Test",
        )
        .unwrap();
    s.set_check(pending, &["command".into()], "/", "Tester")
        .unwrap();
    run(
        &s,
        &s.active_check(pending).unwrap().unwrap(),
        Outcome::Failed,
    );
    assert_eq!(record(&s, pending)["status"], "pending");
    assert_eq!(record(&s, pending)["check"]["state"], "failed");
    let mut expected = Vec::new();
    for outcome in [Outcome::Passed, Outcome::Failed] {
        let id = s
            .remember_scoped(
                "p",
                "long_term",
                "Gemeinsamer Prüfbegriff",
                "geprüft",
                "Test",
            )
            .unwrap();
        s.validate(id, "Tester", "manuelle Fixtureprüfung").unwrap();
        s.set_check(id, &["command".into()], "/", "Tester").unwrap();
        run(&s, &s.active_check(id).unwrap().unwrap(), outcome);
        expected.push(id);
    }
    let hits = serde_json::to_value(s.recall("Prüfbegriff", "p", 5).unwrap()).unwrap();
    assert_eq!(hits.as_array().unwrap().len(), 2);
    assert_eq!(hits[0]["id"], expected[0]);
    assert_eq!(hits[0]["check"]["state"], "passed");
    assert_eq!(hits[1]["id"], expected[1]);
    assert_eq!(hits[1]["check"]["state"], "failed");
    assert_eq!(s.pending("p").unwrap()[0].id, pending);
}
