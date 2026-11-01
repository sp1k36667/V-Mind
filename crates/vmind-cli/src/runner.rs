//! Führt Prüfbefehle aus: festes argv ohne Shell, fester Arbeitsordner, Zeitlimit.
use std::{
    io::Read,
    process::{Command, Stdio},
    thread::{self, JoinHandle},
    time::{Duration, Instant},
};
use vmind_core::{Check, CheckResult, Outcome};

const POLL: Duration = Duration::from_millis(50);
/// Je Ausgabekanal werden höchstens die letzten 64 KiB behalten.
const CAPTURE_BYTES: usize = 65_536;

fn capture(pipe: Option<impl Read + Send + 'static>) -> JoinHandle<Vec<u8>> {
    thread::spawn(move || {
        let mut kept = Vec::new();
        let Some(mut pipe) = pipe else {
            return kept;
        };
        let mut chunk = [0; 8192];
        while let Ok(n) = pipe.read(&mut chunk) {
            if n == 0 {
                break;
            }
            kept.extend_from_slice(&chunk[..n]);
            if kept.len() > CAPTURE_BYTES {
                kept.drain(..kept.len() - CAPTURE_BYTES);
            }
        }
        kept
    })
}

fn collect(handle: JoinHandle<Vec<u8>>) -> String {
    String::from_utf8_lossy(&handle.join().unwrap_or_default()).into_owned()
}

fn elapsed_ms(started: Instant) -> u64 {
    u64::try_from(started.elapsed().as_millis()).unwrap_or(u64::MAX)
}

fn error(started: Instant, output: String) -> CheckResult {
    CheckResult {
        outcome: Outcome::Error,
        exit_code: None,
        duration_ms: elapsed_ms(started),
        output,
    }
}

pub fn run(check: &Check, timeout: Duration) -> CheckResult {
    let started = Instant::now();
    let Some((program, args)) = check.argv.split_first() else {
        return error(started, "Prüfbefehl ist leer".into());
    };
    let spawned = Command::new(program)
        .args(args)
        .current_dir(&check.workdir)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn();
    let mut child = match spawned {
        Ok(child) => child,
        Err(e) => return error(started, format!("Befehl nicht startbar: {e}")),
    };
    let stdout = capture(child.stdout.take());
    let stderr = capture(child.stderr.take());
    loop {
        match child.try_wait() {
            Ok(Some(status)) => {
                // Auch nach dem Ende des Elternprozesses kann ein Kind dessen Pipes
                // offen halten. Das ursprüngliche Zeitlimit gilt bis zum vollständigen
                // Lesen der Ausgabe; ein blockierendes join würde es sonst umgehen.
                while !stdout.is_finished() || !stderr.is_finished() {
                    if started.elapsed() >= timeout {
                        return error(
                            started,
                            format!(
                                "Zeitlimit von {} s beim Lesen der Prüfausgabe überschritten",
                                timeout.as_secs()
                            ),
                        );
                    }
                    thread::sleep(POLL);
                }
                let output = format!("{}{}", collect(stdout), collect(stderr));
                let outcome = if status.success() {
                    Outcome::Passed
                } else {
                    Outcome::Failed
                };
                return CheckResult {
                    outcome,
                    exit_code: status.code().map(i64::from),
                    duration_ms: elapsed_ms(started),
                    output,
                };
            }
            Ok(None) if started.elapsed() < timeout => thread::sleep(POLL),
            Ok(None) => {
                let _ = child.kill();
                let _ = child.wait();
                // Ausgabe nicht abwarten: Unterprozesse könnten die Kanäle offen halten.
                let secs = timeout.as_secs();
                return error(started, format!("Zeitlimit von {secs} s überschritten"));
            }
            Err(e) => {
                let _ = child.kill();
                let _ = child.wait();
                return error(started, format!("Status nicht lesbar: {e}"));
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn check(argv: &[&str]) -> Check {
        Check {
            id: 1,
            memory_id: 1,
            argv: argv.iter().map(|s| s.to_string()).collect(),
            workdir: std::env::temp_dir().to_string_lossy().into_owned(),
            set_by: "Test".into(),
            created_at: String::new(),
        }
    }
    const LIMIT: Duration = Duration::from_secs(10);

    #[test]
    fn exit_codes_map_to_passed_and_failed_with_output() {
        let passed = run(&check(&["sh", "-c", "echo ok"]), LIMIT);
        assert_eq!(passed.outcome, Outcome::Passed);
        assert_eq!(passed.exit_code, Some(0));
        assert_eq!(passed.output.trim(), "ok");
        let failed = run(&check(&["sh", "-c", "echo kaputt >&2; exit 3"]), LIMIT);
        assert_eq!(failed.outcome, Outcome::Failed);
        assert_eq!(failed.exit_code, Some(3));
        assert!(failed.output.contains("kaputt"));
    }

    #[test]
    fn arguments_are_not_interpreted_by_a_shell() {
        let result = run(&check(&["echo", "a;", "exit", "1", "&&", "$HOME"]), LIMIT);
        assert_eq!(result.outcome, Outcome::Passed);
        assert_eq!(result.output.trim(), "a; exit 1 && $HOME");
    }

    #[test]
    fn missing_program_and_missing_directory_are_errors() {
        let missing = run(&check(&["vmind-gibt-es-nicht"]), LIMIT);
        assert_eq!(missing.outcome, Outcome::Error);
        let mut elsewhere = check(&["true"]);
        elsewhere.workdir = "/vmind/gibt/es/nicht".into();
        assert_eq!(run(&elsewhere, LIMIT).outcome, Outcome::Error);
    }

    #[test]
    fn timeout_is_an_error_not_a_failure() {
        let result = run(&check(&["sleep", "5"]), Duration::from_millis(200));
        assert_eq!(result.outcome, Outcome::Error);
        assert!(result.output.contains("Zeitlimit"));
        assert!(result.duration_ms < 4000);
    }

    #[test]
    fn large_output_is_capped_to_the_end() {
        let result = run(
            &check(&[
                "sh",
                "-c",
                "head -c 200000 /dev/zero | tr '\\0' x; echo ENDE",
            ]),
            LIMIT,
        );
        assert_eq!(result.outcome, Outcome::Passed);
        assert!(result.output.len() <= CAPTURE_BYTES);
        assert!(result.output.trim_end().ends_with("ENDE"));
    }
    #[cfg(unix)]
    #[test]
    fn descendant_open_stdout_respects_timeout() {
        // Der Elternprozess beendet sich erfolgreich; sein Kind hält stdout offen.
        let result = run(
            &check(&["sh", "-c", "sleep 3 & echo parent-done"]),
            Duration::from_millis(200),
        );
        assert_eq!(result.outcome, Outcome::Error);
        assert!(result.output.contains("Zeitlimit"));
        assert!(
            result.duration_ms < 2000,
            "Ausgabe darf das Zeitlimit nicht umgehen"
        );
    }
}
