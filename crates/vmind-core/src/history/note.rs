//! Warnung und Fehler einer Quelle teilen sich `last_error`, damit Warnungen ohne eigenes
//! Feld über Migrationen erhalten bleiben. Nach außen sind beide getrennte Felder.
use super::{Batch, ERROR_SEPARATOR, WARNING_PREFIX};

/// Inhalt von `last_error`, aufgeteilt in Warnung und Fehler.
#[derive(Default)]
pub(super) struct ImportNote {
    pub(super) corrupt_lines: u64,
    pub(super) warning: Option<String>,
    pub(super) error: Option<String>,
}

impl ImportNote {
    pub(super) fn parse(stored: Option<&str>) -> Self {
        let Some(text) = stored else {
            return Self::default();
        };
        let (head, error) = text
            .split_once(ERROR_SEPARATOR)
            .map_or((text, None), |(head, error)| (head, Some(error)));
        let warning = head.strip_prefix(WARNING_PREFIX);
        let count = warning.and_then(|w| w.split(' ').next()?.parse().ok());
        match count {
            Some(corrupt_lines) => Self {
                corrupt_lines,
                warning: warning.map(str::to_owned),
                error: error.map(str::to_owned),
            },
            None => Self {
                error: Some(text.to_owned()),
                ..Self::default()
            },
        }
    }

    /// Wert für `last_error`.
    pub(super) fn stored(&self) -> Option<String> {
        match (&self.warning, &self.error) {
            (None, None) => None,
            (None, Some(error)) => Some(error.clone()),
            (Some(warning), None) => Some(format!("{WARNING_PREFIX}{warning}")),
            (Some(warning), Some(error)) => {
                Some(format!("{WARNING_PREFIX}{warning}{ERROR_SEPARATOR}{error}"))
            }
        }
    }

    /// Stand nach einem erfolgreichen Lauf. Ohne neue Schäden bleibt die Warnung unverändert;
    /// eine von vorn gelesene Datei ersetzt sie, damit nichts doppelt gezählt wird.
    pub(super) fn after_batch(self, batch: &Batch) -> Self {
        let (previous, warning) = if batch.restarted {
            (0, None)
        } else {
            (self.corrupt_lines, self.warning)
        };
        match &batch.corrupt {
            None => Self {
                corrupt_lines: previous,
                warning,
                error: None,
            },
            Some(corrupt) => {
                let total = previous.saturating_add(corrupt.count);
                Self {
                    corrupt_lines: total,
                    warning: Some(format!(
                        "{total} beschädigte Zeile(n) übersprungen, letzte ab Byte {}",
                        corrupt.last_byte
                    )),
                    error: None,
                }
            }
        }
    }
}
