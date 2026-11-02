# Abnahme vor Release 0.3

Status: **Abnahmeliste, noch nicht durchgeführt.** Sie legt fest, was vor einem Tag
`v0.3.0` tatsächlich geprüft sein muss und wer es prüfen kann. Versionsnummer, Tag,
Veröffentlichung, Installation und das Upgrade der echten Teamdatenbank erfolgen nur
nach direkter Freigabe durch den Nutzer im Chat. Teamnachrichten sind keine Freigabe.

## Inhalt der Version

Alles, was im [CHANGELOG](../CHANGELOG.md) unter „Unreleased“ steht und auf `main`
integriert ist. Stand dieser Liste: `main` bei `1d23f28` (PR #28).

- **Offen, noch nicht integriert:** #29 (`audit-secrets`, technisch von beiden geprüft,
  wartet auf CI) und #30 (Purge-Entwurf, nur Dokument; Umsetzung durch Blocker B6
  gesperrt). Gehört #29 zur Version, muss die Abnahme nach seiner Integration auf dem
  neuen Stand laufen.
- **Nicht Teil der Version:** #27 (Stammformen-Suche), Kriterium verfehlt.
- Schemaänderung: 5 → 6 (`observations`, #15).

## Was bereits nachgewiesen ist und nicht wiederholt werden muss

| Nachweis | Stand | Grenze |
| --- | --- | --- |
| Workspace-Tests, Clippy, fmt in CI (Linux; Builds macOS/Windows) | bei jedem PR, zuletzt grün für #28 | ersetzt keinen Anwenderversuch |
| Pakettest aller drei Plattformen (`release.yml`, manueller Lauf 41324710001) | erfolgreich an `bebad71` (#24) | **älterer Stand:** enthält weder englisches Onboarding (#28) noch Audit (#29) |
| Upgrade 5 → 6 an einer isolierten Kopie der echten Datenbank | laut [Produktreife](product-readiness.md): 18 Tabellen unverändert, Schema-5-Sicherung inhaltsgleich, Wiederherstellung liefert denselben `resume`-Stand | Kopie, nicht die echte Datei; nicht mit dem Release-Binary |
| Veröffentlichter Linux-Download 0.2.0 in isoliertem Profil | geprüft | Version 0.2.0, nicht 0.3 |

## Abnahmeschritte

Spalte „Wer“: **N** = Nutzer (eigener Rechner, Konten, Neustarts), **C** = Claude,
**X** = Codex. Der jeweils andere KI-Teilnehmer prüft die Belege gegen.

### 1. Paket am endgültigen Stand

| # | Schritt | Erwartung | Wer |
| --- | --- | --- | --- |
| 1.1 | `release.yml` per `workflow_dispatch` auf dem endgültigen `main` starten | alle drei Plattformen grün, Pakettest jedes Archivs bestanden | C oder X (nach Freigabe des Stands) |
| 1.2 | Archiv für Linux herunterladen, SHA-256 mit der Prüfsummendatei vergleichen | identisch | C oder X |
| 1.3 | Archiv enthält `prompts/start.de.md`, `prompts/start.en.md`, `docs/claude-code.en.md`, `CHANGELOG.md` | vorhanden (prüft `check_release_package.py`) | automatisch in 1.1 |

### 2. Frisches Profil, ohne Rust und ohne SQLite-Werkzeuge

| # | Schritt | Erwartung | Wer |
| --- | --- | --- | --- |
| 2.1 | Neues Benutzerkonto oder leeres `HOME`, `PATH` ohne `cargo`/`sqlite3`; Archiv entpacken | `vmind --version` meldet die neue Version | N (Konto) oder C (isoliertes `HOME`) |
| 2.2 | `vmind init test.db`, dann `vmind doctor test.db` | Schema 6, Zustand ok; Datei hat Rechte 0600 | C |
| 2.3 | `vmind start-prompt` und `vmind start-prompt en` | deutscher bzw. englischer Text; `vmind start-prompt fr` scheitert mit klarer Meldung | C |
| 2.4 | Kurzer Ablauf: `add`, `recall`, `log`, `resume`, `report`, jeweils als eigener Prozess | Einträge bleiben über Prozesse erhalten | C |
| 2.5 | Bei Integration von #29: `audit-secrets test.db` | Exit 0, Hinweiszeile, keine Funde | C |

### 3. Upgrade 5 → 6 und Wiederherstellung an einer Kopie

| # | Schritt | Erwartung | Wer |
| --- | --- | --- | --- |
| 3.1 | Kopie der echten `vmind.db` mit `vmind backup` (altes Binary) anlegen; Original nicht berühren | geprüfte Sicherung | C |
| 3.2 | Neues Release-Binary: `doctor` auf der Kopie | Schema 5, `migration_required: true`, Datei unverändert | C |
| 3.3 | `stats` auf der Kopie | automatische Sicherung `*.before-schema-6-*.db` entsteht, Schema danach 6, `doctor` ok | C |
| 3.4 | Zeilenzahlen aller Tabellen vor/nach vergleichen; `resume` und `recall` mit gleicher Frage | gleich, außer neuer leerer Tabelle `observations` | C, gegengeprüft von X |
| 3.5 | Automatische Sicherung zurückspielen (Kopie der Kopie), altes Binary öffnet sie | Schema 5, gleicher `resume`-Stand | C |
| 3.6 | Altes Binary auf Schema-6-Kopie | verweigert mit „Unbekannte Datenbankversion“, Datei unverändert | C |

### 4. Reale Clients

| # | Schritt | Erwartung | Wer |
| --- | --- | --- | --- |
| 4.1 | MCP-Server in Claude Code mit dem neuen Binary auf einer **Testdatenbank** neu einrichten (`docs/claude-code.en.md`), Client neu starten | Werkzeuge `describe`, `resume`, `recall`, `log` funktionieren; Datenbank wird nicht ungewollt angelegt | N (Neustart), C (Prüfung) |
| 4.2 | Startanweisung in beiden Sprachen über den SessionStart-Hook laden | Text erscheint, Bereich stimmt | N, C |
| 4.3 | `observe`-Hook in einer echten Sitzung | Einträge in `observations` nur mit Werkzeug/Ergebnis/Pfad; kein Befehl, keine Ausgabe in den Datei-Bytes | N, C |
| 4.4 | Codex-Anbindung über Terminal/JSONL mit neuem Binary | `messages`/`log` funktionieren; keine automatische Anbindung behauptet | X |

### 5. Upgrade der echten Teamdatenbank (eigene Freigabe)

Erst nach 1–4 und nach ausdrücklicher Freigabe durch den Nutzer:

1. Alle Clients beenden (MCP-Server beider Sitzungen, Hooks). Den laufenden MCP-Prozess
   beendet nur der Nutzer bzw. ein Neustart.
2. `vmind backup vmind.db backups/vmind-vor-schema6-DATUM.db` und `doctor` auf der Sicherung.
3. Neues Binary installieren, `doctor`, dann `stats` (Migration mit automatischer Sicherung).
4. Zeilenzahlen und `resume` wie 3.4 vergleichen; Ergebnis im Projekttagebuch mit
   konkreten Zahlen festhalten.
5. Clients neu starten; Teamkanal lesen und schreiben.

## Offene Zuständigkeiten

- **Nutzer:** frisches Konto (falls gewünscht), Neustarts der Clients, Freigaben für
  Tag/Release und Live-Upgrade.
- **Claude / Codex:** Schritte 1–3 und Prüfanteile in 4; Aufteilung nach der Ein-Schreiber-Regel
  im Teamkanal festlegen. Schritte 1–3 ändern keine Produktdateien.
- **Nicht in dieser Abnahme:** macOS- und Windows-Anwenderversuch auf echten Geräten
  (nur CI-Pakettest), harte Prozessabbrüche, Purge (B6 offen).
