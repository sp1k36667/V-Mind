//! Heuristische Erkennung bekannter Geheimnisformate. Erkennt nur die hier genannten
//! Formate; kein Fund heißt nicht geheimnisfrei. Rückgabe ist nur die Fundart, nie der
//! gefundene Text, damit Aufrufer ihn nicht versehentlich ausgeben.
use serde::Serialize;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SecretKind {
    PrivateKey,
    GithubToken,
    SkApiKey,
    StripeLiveKey,
    AwsAccessKey,
    SlackToken,
    GoogleApiKey,
    /// Unsicher: auch Beispiel- und abgelaufene Tokens haben dieses Format.
    Jwt,
    /// Unsicher: Dokumentationsbeispiele sehen gleich aus.
    UrlCredentials,
}

impl SecretKind {
    pub fn label(self) -> &'static str {
        match self {
            Self::PrivateKey => "Privater Schlüssel",
            Self::GithubToken => "GitHub-Token",
            Self::SkApiKey => "API-Schlüssel (sk-)",
            Self::StripeLiveKey => "Stripe-Live-Schlüssel",
            Self::AwsAccessKey => "AWS-Zugangsschlüssel",
            Self::SlackToken => "Slack-Token",
            Self::GoogleApiKey => "Google-API-Schlüssel",
            Self::Jwt => "JWT",
            Self::UrlCredentials => "Zugangsdaten in URL",
        }
    }

    pub fn certain(self) -> bool {
        !matches!(self, Self::Jwt | Self::UrlCredentials)
    }
}

fn is_alnum(c: u8) -> bool {
    c.is_ascii_alphanumeric()
}

fn is_word(c: u8) -> bool {
    is_alnum(c) || c == b'_'
}

fn is_dash_word(c: u8) -> bool {
    is_word(c) || c == b'-'
}

/// Kein Buchstabe, keine Ziffer und kein Unterstrich direkt vor dem Präfix.
fn boundary_before(bytes: &[u8], start: usize) -> bool {
    start == 0 || !is_word(bytes[start - 1])
}

/// Länge des Laufs zulässiger Zeichen ab `start`.
fn run(bytes: &[u8], start: usize, allowed: fn(u8) -> bool) -> usize {
    bytes[start..].iter().take_while(|&&c| allowed(c)).count()
}

fn mixed(bytes: &[u8]) -> bool {
    bytes.iter().any(u8::is_ascii_digit) && bytes.iter().any(u8::is_ascii_alphabetic)
}

/// Startpositionen eines Präfixes mit Wortgrenze davor.
fn starts<'a>(text: &'a str, prefix: &'a str) -> impl Iterator<Item = usize> + 'a {
    let bytes = text.as_bytes();
    text.match_indices(prefix)
        .map(|(i, _)| i)
        .filter(move |&i| boundary_before(bytes, i))
}

/// Präfix gefolgt von mindestens `min` zulässigen Zeichen, darunter Buchstaben und Ziffern.
fn prefixed(text: &str, prefixes: &[&str], min: usize, allowed: fn(u8) -> bool) -> bool {
    let bytes = text.as_bytes();
    prefixes.iter().any(|prefix| {
        starts(text, prefix).any(|i| {
            let body = i + prefix.len();
            let len = run(bytes, body, allowed);
            len >= min && mixed(&bytes[body..body + len])
        })
    })
}

fn private_key(text: &str) -> bool {
    text.match_indices("-----BEGIN ").any(|(i, _)| {
        let rest = &text[i..];
        let header = rest.find('\n').map_or(rest, |end| &rest[..end]);
        header.contains("PRIVATE KEY-----")
    })
}

fn aws(text: &str) -> bool {
    let bytes = text.as_bytes();
    ["AKIA", "ASIA"].iter().any(|prefix| {
        starts(text, prefix).any(|i| {
            let body = i + prefix.len();
            let len = run(bytes, body, |c| {
                c.is_ascii_uppercase() || c.is_ascii_digit()
            });
            len == 16 && bytes.get(body + len).is_none_or(|&c| !is_word(c))
        })
    })
}

fn slack(text: &str) -> bool {
    ["xoxa-", "xoxb-", "xoxp-", "xoxr-", "xoxs-"]
        .iter()
        .any(|p| prefixed(text, &[p], 10, |c| is_alnum(c) || c == b'-'))
}

fn jwt(text: &str) -> bool {
    let bytes = text.as_bytes();
    starts(text, "eyJ").any(|i| {
        let mut pos = i;
        for part in 0..3 {
            let len = run(bytes, pos, is_dash_word);
            if len < 10 || (part == 1 && !bytes[pos..].starts_with(b"eyJ")) {
                return false;
            }
            pos += len;
            if part < 2 {
                if bytes.get(pos) != Some(&b'.') {
                    return false;
                }
                pos += 1;
            }
        }
        true
    })
}

/// `schema://NUTZER:PASSWORT@` mit echtem Passwort; Platzhalter wie `***`, `<passwort>`,
/// `{passwort}` und `$VARIABLE` zählen nicht.
fn url_credentials(text: &str) -> bool {
    let bytes = text.as_bytes();
    text.match_indices("://").any(|(i, _)| {
        let scheme = bytes[..i]
            .iter()
            .rev()
            .take_while(|&&c| is_alnum(c) || b"+.-".contains(&c))
            .count();
        if scheme == 0 {
            return false;
        }
        let rest = &text[i + 3..];
        let end = rest
            .find(|c: char| c == '/' || c == '?' || c == '#' || c.is_whitespace())
            .unwrap_or(rest.len());
        let Some((userinfo, _host)) = rest[..end].rsplit_once('@') else {
            return false;
        };
        let Some((user, password)) = userinfo.split_once(':') else {
            return false;
        };
        !user.is_empty()
            && !password.is_empty()
            && !password.chars().all(|c| c == '*')
            && !password.starts_with(['<', '{', '$', '%'])
    })
}

/// Alle erkannten Fundarten eines Textes, sortiert und ohne Dubletten.
pub fn detect(text: &str) -> Vec<SecretKind> {
    let checks: [(SecretKind, bool); 9] = [
        (SecretKind::PrivateKey, private_key(text)),
        (
            SecretKind::GithubToken,
            prefixed(
                text,
                &["ghp_", "gho_", "ghu_", "ghs_", "ghr_"],
                36,
                is_alnum,
            ) || prefixed(text, &["github_pat_"], 50, is_word),
        ),
        (
            SecretKind::SkApiKey,
            prefixed(text, &["sk-"], 20, is_dash_word),
        ),
        (
            SecretKind::StripeLiveKey,
            prefixed(text, &["sk_live_", "rk_live_"], 20, is_alnum),
        ),
        (SecretKind::AwsAccessKey, aws(text)),
        (SecretKind::SlackToken, slack(text)),
        (
            SecretKind::GoogleApiKey,
            prefixed(text, &["AIza"], 35, is_dash_word),
        ),
        (SecretKind::Jwt, jwt(text)),
        (SecretKind::UrlCredentials, url_credentials(text)),
    ];
    checks
        .into_iter()
        .filter_map(|(kind, found)| found.then_some(kind))
        .collect()
}

#[cfg(test)]
pub(crate) mod samples {
    //! Synthetische Testwerte, zur Laufzeit zusammengesetzt, damit kein Scanner
    //! auf das Repository anschlägt. Keiner davon ist ein echtes Geheimnis.
    use super::SecretKind;

    pub fn all() -> Vec<(SecretKind, String)> {
        let body = |n: usize| "a1B2".repeat(n.div_ceil(4))[..n].to_string();
        vec![
            (
                SecretKind::PrivateKey,
                format!("-----BEGIN {}PRIVATE KEY-----\nabc", "RSA "),
            ),
            (SecretKind::GithubToken, format!("gh{}_{}", "p", body(36))),
            (
                SecretKind::GithubToken,
                format!("github{}pat_{}", "_", body(60)),
            ),
            (SecretKind::SkApiKey, format!("s{}-ant-{}", "k", body(40))),
            (
                SecretKind::StripeLiveKey,
                format!("sk_{}_{}", "live", body(24)),
            ),
            (
                SecretKind::AwsAccessKey,
                format!("AK{}{}", "IA", "Z9Y8X7W6V5U4T3S2"),
            ),
            (SecretKind::SlackToken, format!("xo{}-{}", "xb", body(24))),
            (SecretKind::GoogleApiKey, format!("AI{}{}", "za", body(35))),
            (
                SecretKind::Jwt,
                format!(
                    "ey{}.eyJ{}.{}",
                    "J".to_owned() + &body(12),
                    body(12),
                    body(12)
                ),
            ),
            (
                SecretKind::UrlCredentials,
                format!("postgres://app:{}@db.example/x", body(12)),
            ),
        ]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn each_synthetic_sample_is_detected_as_its_kind() {
        for (kind, value) in samples::all() {
            let text = format!("Fehler mit {value} im Log");
            assert_eq!(detect(&text), vec![kind], "{}", kind.label());
        }
    }

    #[test]
    fn ordinary_text_and_placeholders_are_not_reported() {
        let hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
        for text in [
            "Token abgelaufen; neues Passwort setzen",
            "pip install scikit-learn; sk-learn ist falsch geschrieben",
            "postgres://localhost/db und https://example.org/a:b@c",
            "Passwort: *** und postgres://app:***@db/x",
            "postgres://app:<passwort>@db/x und mysql://u:$DB_PASS@h/x",
            "https://user@example.org/pfad",
            hash,
            "550e8400-e29b-41d4-a716-446655440000",
            "task-abcdefghijklmnopqrstuvwxyz und risk-1234567890123456789012",
            "AKIAKURZ und -----BEGIN PUBLIC KEY-----",
        ] {
            assert!(detect(text).is_empty(), "Fehlalarm: {text}");
        }
    }

    #[test]
    fn prefix_inside_a_word_is_not_a_match() {
        let value = format!("xgh{}_{}", "p", "a1B2".repeat(9));
        assert!(detect(&value).is_empty());
    }

    #[test]
    fn jwt_and_url_credentials_are_marked_uncertain() {
        assert!(!SecretKind::Jwt.certain());
        assert!(!SecretKind::UrlCredentials.certain());
        assert!(SecretKind::GithubToken.certain());
    }
}
