use vmind_core::{CheckResult, MemoryStore, Outcome};

fn argv(parts: &[&str]) -> Vec<String> {
    parts.iter().map(|s| s.to_string()).collect()
}
fn result(outcome: Outcome, exit_code: Option<i64>, output: &str) -> CheckResult {
    CheckResult {
        outcome,
        exit_code,
        duration_ms: 12,
        output: output.into(),
    }
}
fn store_with_entry(scope: &str) -> (MemoryStore, i64) {
    let store = MemoryStore::in_memory().unwrap();
    let id = store
        .remember_scoped(
            scope,
            "error_solution",
            "JSON kaputt",
            "Nicht überschreiben",
            "Test",
        )
        .unwrap();
    (store, id)
}

#[test]
fn passing_check_validates_pending_entry_with_traceable_evidence() {
    let (s, id) = store_with_entry("p");
    s.set_check(
        id,
        &argv(&["pytest", "-k", "corrupt"]),
        "/tmp/projekt",
        "Testleiter",
    )
    .unwrap();
    let check = s.active_check(id).unwrap().unwrap();
    assert!(s.recall("JSON", "p", 5).unwrap().is_empty());

    let applied = s
        .apply_check(&check, &result(Outcome::Passed, Some(0), "1 passed"), false)
        .unwrap();

    assert_eq!(applied.status_before, "pending");
    assert_eq!(applied.status_after, "validated");
    let record = s.get(id).unwrap().unwrap();
    assert_eq!(record.validated_by.as_deref(), Some("vmind check"));
    let evidence = record.evidence.unwrap();
    assert!(evidence.contains("pytest -k corrupt") && evidence.contains("/tmp/projekt"));
    assert_eq!(s.recall("JSON", "p", 5).unwrap()[0].id, id);
    assert_eq!(s.check_runs(id, 10).unwrap()[0].output, "1 passed");
}

#[test]
fn failing_check_reports_only_unless_invalidation_is_requested() {
    let (s, id) = store_with_entry("p");
    s.validate(id, "Prüfer", "Handtest").unwrap();
    s.set_check(id, &argv(&["cargo", "test"]), "/repo", "Testleiter")
        .unwrap();
    let check = s.active_check(id).unwrap().unwrap();
    let failed = result(Outcome::Failed, Some(101), "1 failed");

    let reported = s.apply_check(&check, &failed, false).unwrap();
    assert_eq!(reported.status_after, "validated");

    let withdrawn = s.apply_check(&check, &failed, true).unwrap();
    assert_eq!(withdrawn.status_after, "invalidated");
    let record = s.get(id).unwrap().unwrap();
    assert_eq!(record.invalidated_by.as_deref(), Some("vmind check"));
    assert!(record.invalidation_reason.unwrap().contains("Exit 101"));
    assert_eq!(s.check_runs(id, 10).unwrap().len(), 2);
}

#[test]
fn errors_and_failures_never_validate_and_errors_never_invalidate() {
    let (s, id) = store_with_entry("p");
    s.set_check(id, &argv(&["fehlt"]), "/nirgends", "Testleiter")
        .unwrap();
    let check = s.active_check(id).unwrap().unwrap();
    for outcome in [Outcome::Error, Outcome::Failed] {
        let applied = s
            .apply_check(&check, &result(outcome, None, "x"), true)
            .unwrap();
        assert_eq!(applied.status_after, "pending");
    }
    s.validate(id, "Prüfer", "Handtest").unwrap();
    let applied = s
        .apply_check(&check, &result(Outcome::Error, None, "Zeitlimit"), true)
        .unwrap();
    assert_eq!(applied.status_after, "validated");
}

#[test]
fn set_check_rejects_invalid_input_and_withdrawn_entries() {
    let (s, id) = store_with_entry("p");
    assert!(s.set_check(id, &[], "/repo", "T").is_err());
    assert!(s.set_check(id, &argv(&[" "]), "/repo", "T").is_err());
    assert!(s.set_check(id, &argv(&["true"]), " ", "T").is_err());
    assert!(s.set_check(id, &argv(&["true"]), "/repo", "").is_err());
    assert!(
        s.set_check(id + 99, &argv(&["true"]), "/repo", "T")
            .is_err()
    );
    let huge = "x".repeat(4001);
    assert!(s.set_check(id, &argv(&[&huge]), "/repo", "T").is_err());
    s.invalidate(id, "Prüfer", "falsch").unwrap();
    assert!(s.set_check(id, &argv(&["true"]), "/repo", "T").is_err());
}

#[test]
fn replaced_check_cannot_be_applied_and_scope_lists_only_active_checks() {
    let (s, id) = store_with_entry("p");
    let other = s
        .remember_scoped("q", "long_term", "Anderes", "Projekt", "Test")
        .unwrap();
    let withdrawn = s
        .remember_scoped("p", "long_term", "Alt", "Weg", "Test")
        .unwrap();
    s.set_check(id, &argv(&["alt"]), "/repo", "T").unwrap();
    let old = s.active_check(id).unwrap().unwrap();
    s.set_check(id, &argv(&["neu"]), "/repo", "T").unwrap();
    s.set_check(other, &argv(&["q"]), "/repo", "T").unwrap();
    s.set_check(withdrawn, &argv(&["w"]), "/repo", "T").unwrap();
    s.invalidate(withdrawn, "Prüfer", "veraltet").unwrap();

    assert!(
        s.apply_check(&old, &result(Outcome::Passed, Some(0), ""), false)
            .is_err()
    );
    let listed = s.checks_in_scope("p").unwrap();
    assert_eq!(listed.len(), 1);
    assert_eq!(listed[0].argv, argv(&["neu"]));
    assert_eq!(s.get(id).unwrap().unwrap().status, "pending");
}

#[test]
fn long_output_keeps_the_end() {
    let (s, id) = store_with_entry("p");
    s.set_check(id, &argv(&["t"]), "/repo", "T").unwrap();
    let check = s.active_check(id).unwrap().unwrap();
    let output = format!("{}ENDE", "ä".repeat(5000));
    s.apply_check(&check, &result(Outcome::Failed, Some(1), &output), false)
        .unwrap();
    let stored = &s.check_runs(id, 1).unwrap()[0].output;
    assert_eq!(stored.chars().count(), 4000);
    assert!(stored.ends_with("ENDE"));
}

#[test]
fn command_line_quotes_arguments_with_spaces_or_special_characters() {
    let (s, id) = store_with_entry("p");
    s.set_check(
        id,
        &argv(&[
            "sh",
            "-c",
            "cargo test 2>&1 | grep -q '0 passed'",
            "",
            "a.b=c",
        ]),
        "/repo",
        "T",
    )
    .unwrap();
    let check = s.active_check(id).unwrap().unwrap();
    assert_eq!(
        check.command_line(),
        r"sh -c 'cargo test 2>&1 | grep -q '\''0 passed'\''' '' a.b=c"
    );
}
