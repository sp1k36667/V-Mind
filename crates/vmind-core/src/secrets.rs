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

/// Byte-Bereich eines Fundes im Text.
type Span = (usize, usize);

/// Präfix gefolgt von mindestens `min` zulässigen Zeichen, darunter Buchstaben und Ziffern.
fn prefixed(text: &str, prefixes: &[&str], min: usize, allowed: fn(u8) -> bool) -> Vec<Span> {
    let bytes = text.as_bytes();
    let mut spans = Vec::new();
    for prefix in prefixes {
        for i in starts(text, prefix) {
            let body = i + prefix.len();
            let len = run(bytes, body, allowed);
            if len >= min && mixed(&bytes[body..body + len]) {
                spans.push((i, body + len));
            }
        }
    }
    spans
}

/// Vom Kopf bis zum passenden Ende; ohne Ende bis zum Textende.
fn private_key(text: &str) -> Vec<Span> {
    const END: &str = "-----END ";
    const DASHES: &str = "-----";
    text.match_indices("-----BEGIN ")
        .filter_map(|(i, _)| {
            let rest = &text[i..];
            let header = rest.find('\n').map_or(rest, |end| &rest[..end]);
            if !header.contains("PRIVATE KEY-----") {
                return None;
            }
            let end = rest.find(END).and_then(|at| {
                let body = at + END.len();
                rest[body..].find(DASHES).map(|d| body + d + DASHES.len())
            });
            Some((i, end.map_or(text.len(), |e| i + e)))
        })
        .collect()
}

fn aws(text: &str) -> Vec<Span> {
    let bytes = text.as_bytes();
    let mut spans = Vec::new();
    for prefix in ["AKIA", "ASIA"] {
        for i in starts(text, prefix) {
            let body = i + prefix.len();
            let len = run(bytes, body, |c| {
                c.is_ascii_uppercase() || c.is_ascii_digit()
            });
            if len == 16 && bytes.get(body + len).is_none_or(|&c| !is_word(c)) {
                spans.push((i, body + len));
            }
        }
    }
    spans
}

fn slack(text: &str) -> Vec<Span> {
    ["xoxa-", "xoxb-", "xoxp-", "xoxr-", "xoxs-"]
        .iter()
        .flat_map(|p| prefixed(text, &[p], 10, |c| is_alnum(c) || c == b'-'))
        .collect()
}

fn jwt(text: &str) -> Vec<Span> {
    let bytes = text.as_bytes();
    starts(text, "eyJ")
        .filter_map(|i| {
            let mut pos = i;
            for part in 0..3 {
                let len = run(bytes, pos, is_dash_word);
                if len < 10 || (part == 1 && !bytes[pos..].starts_with(b"eyJ")) {
                    return None;
                }
                pos += len;
                if part < 2 {
                    if bytes.get(pos) != Some(&b'.') {
                        return None;
                    }
                    pos += 1;
                }
            }
            Some((i, pos))
        })
        .collect()
}

/// `schema://NUTZER:PASSWORT@` mit echtem Passwort; Platzhalter wie `***`, `<passwort>`,
/// `{passwort}` und `$VARIABLE` zählen nicht. Die Fundstelle umfasst Nutzer und Passwort,
/// weil manche Dienste das Token als Nutzernamen erwarten.
fn url_credentials(text: &str) -> Vec<Span> {
    let bytes = text.as_bytes();
    text.match_indices("://")
        .filter_map(|(i, _)| {
            let scheme = bytes[..i]
                .iter()
                .rev()
                .take_while(|&&c| is_alnum(c) || b"+.-".contains(&c))
                .count();
            if scheme == 0 {
                return None;
            }
            let start = i + 3;
            let rest = &text[start..];
            let end = rest
                .find(|c: char| c == '/' || c == '?' || c == '#' || c.is_whitespace())
                .unwrap_or(rest.len());
            let (userinfo, _host) = rest[..end].rsplit_once('@')?;
            let (user, password) = userinfo.split_once(':')?;
            (!user.is_empty()
                && !password.is_empty()
                && !password.chars().all(|c| c == '*')
                && !password.starts_with(['<', '{', '$', '%']))
            .then_some((start, start + userinfo.len()))
        })
        .collect()
}

fn findings(text: &str) -> [(SecretKind, Vec<Span>); 9] {
    let mut github = prefixed(
        text,
        &["ghp_", "gho_", "ghu_", "ghs_", "ghr_"],
        36,
        is_alnum,
    );
    github.extend(prefixed(text, &["github_pat_"], 50, is_word));
    [
        (SecretKind::PrivateKey, private_key(text)),
        (SecretKind::GithubToken, github),
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
    ]
}

/// Alle erkannten Fundarten eines Textes, sortiert und ohne Dubletten.
pub fn detect(text: &str) -> Vec<SecretKind> {
    findings(text)
        .into_iter()
        .filter_map(|(kind, spans)| (!spans.is_empty()).then_some(kind))
        .collect()
}

/// Ersetzt alle Fundstellen bekannter Formate durch Platzhalter mit der Fundart. Keine
/// Garantie: Unbekannte Formate bleiben stehen. Der Platzhalter enthält keinen Doppelpunkt,
/// damit er in einer URL nicht selbst als Zugangsdaten gilt.
pub fn redact(text: &str) -> String {
    let mut spans: Vec<(Span, SecretKind)> = findings(text)
        .into_iter()
        .flat_map(|(kind, spans)| spans.into_iter().map(move |span| (span, kind)))
        .collect();
    spans.sort();
    let mut out = String::with_capacity(text.len());
    let mut pos = 0;
    for ((start, end), kind) in spans {
        if end <= pos {
            continue;
        }
        if start >= pos {
            out.push_str(&text[pos..start]);
            out.push_str(&format!("[REDIGIERT {}]", kind.label()));
        }
        // Überlappung: Der bisherige Platzhalter deckt auch diesen Fund ab.
        pos = end;
    }
    out.push_str(&text[pos..]);
    out
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
    fn redact_removes_each_sample_and_keeps_the_surroundings() {
        for (kind, value) in samples::all() {
            let text = format!("vorher {value} nachher");
            let clean = redact(&text);
            assert!(!clean.contains(&value), "{}", kind.label());
            assert!(detect(&clean).is_empty(), "{clean}");
            assert!(clean.starts_with("vorher "), "{clean}");
            assert!(clean.contains(kind.label()), "{clean}");
        }
    }

    #[test]
    fn redact_removes_a_whole_private_key_block_and_the_rest_without_end_marker() {
        let block = format!(
            "a -----BEGIN {0}PRIVATE KEY-----\nGEHEIM\n-----END {0}PRIVATE KEY----- b",
            "RSA "
        );
        assert_eq!(redact(&block), "a [REDIGIERT Privater Schlüssel] b");
        let open = format!("a -----BEGIN {}PRIVATE KEY-----\nGEHEIM", "RSA ");
        assert_eq!(redact(&open), "a [REDIGIERT Privater Schlüssel]");
    }

    #[test]
    fn redact_handles_several_and_overlapping_findings_and_leaves_plain_text() {
        let (token, jwt_value) = {
            let all = samples::all();
            let find = |wanted| {
                all.iter()
                    .find(|(k, _)| *k == wanted)
                    .map(|(_, v)| v.clone())
                    .unwrap()
            };
            (find(SecretKind::GithubToken), find(SecretKind::Jwt))
        };
        let clean = redact(&format!("{token} und ä {token}"));
        assert_eq!(clean.matches("[REDIGIERT").count(), 2);
        assert!(clean.contains(" und ä "));
        let nested = redact(&format!("https://{token}:{jwt_value}@host.example/x"));
        assert_eq!(nested.matches("[REDIGIERT").count(), 1, "{nested}");
        assert!(nested.ends_with("@host.example/x"), "{nested}");
        assert!(detect(&nested).is_empty(), "{nested}");
        assert_eq!(redact("nichts Geheimes äöü"), "nichts Geheimes äöü");
    }

    #[test]
    fn jwt_and_url_credentials_are_marked_uncertain() {
        assert!(!SecretKind::Jwt.certain());
        assert!(!SecretKind::UrlCredentials.certain());
        assert!(SecretKind::GithubToken.certain());
    }
}
