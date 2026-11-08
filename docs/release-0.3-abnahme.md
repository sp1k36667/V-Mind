# Abnahme vor Release 0.3

Status: **Abnahmeliste; am Kandidaten 0.3.0-rc.6 Schritte 1–3 und 4.4 bestanden, 4.1–4.3 offen.** Schritt 3 wurde nur an einer synthetischen Schema-5-Datenbank geprüft; die im Plan vorgesehene Kopie der echten Datenbank wurde nicht geprüft. Sie legt fest, was vor einem Tag
`v0.3.0` tatsächlich geprüft sein muss und wer es prüfen kann. Versionsvorbereitung und isolierte Prüfungen gehören zum bestehenden Arbeitsauftrag.
Tag/Veröffentlichung und Änderungen der echten Installation/Teamdatenbank werden
separat mit dem Nutzer koordiniert. Teamnachrichten ersetzen keine Nutzerentscheidung.

## Inhalt der Version

Alles, was im [CHANGELOG](../CHANGELOG.md) unter „Unreleased“ steht und auf `main`
integriert ist. Stand dieser Liste: Audit #29 ist integriert; Purge #30 ist ausschließlich ein
Diskussionsentwurf mit ungelöstem Blocker B6, kein ausführbares Feature.

- **Integriert:** #29 (`audit-secrets`), inklusive unabhängiger Korrektur und grüner
  Plattform-CI. Die nächste Paketabnahme muss diesen neuen Quellstand enthalten.
- **Nicht Teil der Version:** #27 (Stammformen-Suche), Kriterium verfehlt.
- Schemaänderung: 5 → 6 (`observations`, #15).

## Was bereits nachgewiesen ist und nicht wiederholt werden muss

| Nachweis | Stand | Grenze |
| --- | --- | --- |
| Workspace-Tests, Clippy, fmt in CI (Linux; Builds macOS/Windows) | bei jedem PR, zuletzt grün für #29 (112 Tests) | ersetzt keinen Anwenderversuch |
| Pakettest aller drei Plattformen (`release.yml`, manueller Lauf 41324710001) | erfolgreich an `bebad71` (#24) | **älterer Stand:** enthält weder englisches Onboarding (#28) noch Audit (#29) |
| Upgrade 5 → 6 an einer isolierten Kopie der echten Datenbank | laut [Produktreife](product-readiness.md): 18 Tabellen unverändert, Schema-5-Sicherung inhaltsgleich, Wiederherstellung liefert denselben `resume`-Stand | Kopie, nicht die echte Datei; nicht mit dem Release-Binary |
| Veröffentlichter Linux-Download 0.2.0 in isoliertem Profil | geprüft | Version 0.2.0, nicht 0.3 |
| Paketprobe aller drei Plattformen (manueller Lauf 41479924674, laut Codex #150/#152) | erfolgreich an `2a3af39`; Linux-Archiv lokal vollständig geprüft (Pakettest, beide Startsprachen, add/validate/recall, Audit, Upgrade/Restore an Kopie), macOS-Archiv Dateien geprüft | **Entwicklungsartefakt vor der Versionsanhebung:** meldet `0.2.0`, ist aber nicht das veröffentlichte 0.2.0; nur über Commit/SHA-256 eindeutig. Windows-Download wegen HTTP 503 noch nicht lokal geprüft, CI-Pakettest grün. Die laufende MCP-Probe ist auf dieses Artefakt gepinnt |

### Kandidat 0.3.0-rc.1

Ab dem Commit der Versionsanhebung meldet der Quellstand `vmind 0.3.0-rc.1`. Die
Schritte 1–4 laufen am Kandidaten erneut, sobald ein Paket dieses Stands gebaut ist;
Ergebnisse der Artefakte von `2a3af39` gelten als Vorprüfung, nicht als Abnahme des
Kandidaten. Ein Kandidat ist kein Release: Tag, Veröffentlichung und Installation
bleiben getrennte Schritte.

### Ergebnisse am Kandidaten (Stand 2. November 2026)

Quelle: `7e92e002afd3ac3874a31780cbb44292062da32d` (Merge von #32), Paketlauf
`release.yml` 41483780591 per `workflow_dispatch`: alle drei Builds erfolgreich,
Veröffentlichung übersprungen. Codex hat die Archive heruntergeladen und die Ergebnisse
in einer lokalen Beleg-Datei festgehalten (nur synthetische Daten und Statuswerte);
Claude hat die Prüfsummen und eine Stichprobe unabhängig nachvollzogen.

| Archiv | SHA-256 (selbst nachgerechnet von Codex und Claude) |
| --- | --- |
| `vmind-7e92e00…-linux-x86_64.tar.gz` | `d8b2482b165249d2695ce546ffd7a6872aed81bc49d56f2450ae73c7bc0a810a` |
| `vmind-7e92e00…-macos-arm64.tar.gz` | `653c35fbb1b4fc5629917f6b6d751b67f870469c0cd3e42dcbf91a9ae0cc3fd4` |
| `vmind-7e92e00…-windows-x86_64.zip` | `a18a7254c72dda6faffa8da6303068cff035a13e05745aac0dfd921d19bef977` |

| Schritt | Ergebnis | Wer, wo |
| --- | --- | --- |
| 1.1 Paket am Stand | bestanden: drei Builds samt Pakettest jedes Archivs in CI | CI |
| 1.2 Prüfsummen | protokolliert (oben); Vergleich mit veröffentlichter `SHA256SUMS.txt` erst beim Release | X, gegengerechnet C |
| 1.3 Dateien im Archiv | bestanden (Linux lokal: 105 Links, 10 Prozessaufrufe) | X |
| 2.1 leeres Profil | Linux bestanden: `vmind 0.3.0-rc.1` mit leerem `PATH` und eigenem `HOME` | X; Stichprobe C |
| 2.2 init/doctor | Linux bestanden: Schema 6, Rechte 0600 | X; Stichprobe C (0600) |
| 2.3 Startsprachen | Linux bestanden: de, en; `fr` mit klarer Meldung abgewiesen | X; Stichprobe C |
| 2.4 Ablauf | Linux bestanden: ungeprüfter Eintrag nicht im Abruf, nach `validate` im Abruf | X |
| 2.5 Audit | Linux bestanden: leere Datenbank ohne Fund | X; Stichprobe C |
| — fehlende Datenbank | Linux bestanden: wird nicht angelegt | X; Stichprobe C |
| 3.1–3.6 Upgrade an Kopie | Linux bestanden: 18 vorhandene Tabellen unverändert, automatische Sicherung inhaltsgleich, Wiederherstellung liefert gleichen `resume`-Stand; echte Datenbank weiter Schema 5 | X |
| 4.1 MCP | **offen.** Nur Protokollebene geprüft (Serverversion im MCP-Handshake korrekt); ein realer Desktop-Client-Test fehlt, die Probedatenbank ist leer | N, C |
| 4.2–4.4 | **offen** | N, C, X |

Grenzen: Lokal ausgeführt wurde nur das Linux-Archiv auf diesem Ubuntu-Rechner. macOS
und Windows sind durch die Pakettests in CI belegt, nicht durch einen Anwenderversuch
auf echten Geräten. Die laufende MCP-Probe ist noch auf das ältere Artefakt von
`2a3af39` gepinnt.

**Noch offen vor einem Release:** Schritt 4 (realer Client), Entscheidung über die
endgültige Versionsnummer, Tag und Veröffentlichung (Nutzerfreigabe) und Schritt 5
(Upgrade der echten Teamdatenbank, eigene Nutzerfreigabe).

### Ergebnisse am Kandidaten 0.3.0-rc.6 (Stand 7. November 2026)

Quelle: `5ae51814b8dc882bfedd3204b00fad16c2685ba2` (Merge von #50, enthält #40, #42–#44,
#46–#51), Paketlauf `release.yml` 42370581822 per `workflow_dispatch`, ausgelöst von Codex:
alle drei Builds samt Pakettest erfolgreich, Veröffentlichung übersprungen. Claude hat das
Linux-Archiv heruntergeladen und isoliert geprüft, nur mit synthetischen Daten im
Arbeitsverzeichnis der Sitzung; keine echte Datenbank, keine Modellaufrufe.

| Archiv | SHA-256 (von Claude und Codex unabhängig nachgerechnet) |
| --- | --- |
| `vmind-5ae5181…-linux-x86_64.tar.gz` | `8dacb6f13eeaf9d0d226e481c1a9db6d885ed88d881a9621f0002207582c0f59` |
| `vmind-5ae5181…-macos-arm64.tar.gz` | `1b6b456a511d1150794d563f0455a5bb1806e657946879faa5f536e0c85ecdd1` |
| `vmind-5ae5181…-windows-x86_64.zip` | `720d435cac1bfaa797403ac44d3ff89df373a6bd31674ed652933944b6aba7c2` |

| Schritt | Ergebnis (Linux-Archiv, lokal) | Wer |
| --- | --- | --- |
| 1.1 Paket am Stand | bestanden: drei Builds samt Pakettest in CI | X (Lauf), CI |
| 1.2 Prüfsummen | protokolliert (oben); Vergleich mit veröffentlichter `SHA256SUMS.txt` erst beim Release | C |
| 1.3 Dateien im Archiv | bestanden: `check_release_package.py` lokal, 140 Links, 10 Prozessaufrufe, isoliertes Profil mit leerem `PATH`, Neustart, Sicherung und Wiederherstellung; keine absoluten Pfade oder `..` im Archiv | C |
| 2.1 leeres Profil | bestanden (im Pakettest); `vmind --version` meldet `vmind 0.3.0-rc.6` | C |
| 2.2 init/doctor | bestanden: Schema 6, Rechte 0600 | C |
| 2.3 Startsprachen | bestanden: de und en nennen `propose_repair`; `fr` mit „Sprache muss de oder en sein“ abgewiesen | C |
| 2.4 Ablauf | bestanden: `add`, `validate`, `recall` mit Wortform („Zertifikate“ findet „Zertifikat“), `recall --limit 0` abgewiesen | C |
| — Reparaturwissen (#46–#48) | bestanden mit echtem Prüfbefehl: `check` meldet nach fehlgeschlagen→bestanden die Reparatur, `resume` zählt 1 offene, `propose-repair` speichert einen Vorschlag, ein zweiter wird abgelehnt, danach 0 offene | C |
| — MCP-Werkzeugliste | bestanden: `repairs` und `propose_repair` vorhanden, kein `validate` | C |
| — Journalmodus (#44) | bestanden: `wal` und zurück zu `delete`, jeweils von `doctor` bestätigt | C |
| 2.5 Audit | bestanden: Exit 0, Hinweiszeile, keine Funde | C |
| 3.1–3.4 Upgrade an Kopie | bestanden an einer **synthetischen** Schema-5-Datenbank, angelegt mit dem installierten 0.2.0 (2 Einträge, Ziel, Aufgabe, Prüfbefehl mit Lauf, Gespräch mit Nachricht): `doctor` liest Schema 5 und lässt die Datei byte-gleich; `stats` migriert auf 6 nach automatischer Sicherung; Sicherung inhaltsgleich mit dem Original (gleicher SQL-Dump; byte-gleich ist sie nicht, die Backup-API schreibt Seiten neu); `doctor` gesund; `resume` (Ziel, Aufgaben, Gespräch, Ereignisse) und `recall` unverändert | C |
| 3.5 Rückweg | bestanden: zurückgespielte Sicherung öffnet das alte Binary als Schema 5 mit gleichem `resume`-Stand | C |
| 3.6 Altes Binary auf Schema 6 | bestanden: verweigert mit „Unbekannte Datenbankversion“, Datei unverändert (SHA-256 gleich) | C |
| — Sicherung | bestanden: `backup` geprüft, überschreibt kein vorhandenes Ziel, Kopie liefert denselben Stand | C |
| 4.1–4.3 Reale Clients | **offen** | N, C |
| 4.4 Codex über JSONL | bestanden am Linux-Archiv, isoliert mit synthetischer Test-DB: `session_new`, `log`, `message`, `messages` | X |

Grenzen: Das Upgrade wurde an einer synthetischen statt an einer Kopie der echten
Datenbank geprüft (Vorgabe Codex #352: keine echten Inhalte in PR, GitHub oder Logs). macOS
und Windows sind nur durch die CI-Pakettests belegt. Unter 3.6 meldet das alte 0.2.0 noch das
missverständliche Präfix „Invalid parameter name:“ (behoben ab #17, betrifft nur das alte
Binary). Prüfskript und Protokoll liegen nur lokal beim Prüfenden.

**Noch offen vor einem Release:** Schritte 4.1–4.3 (realer Client), Entscheidung über die
endgültige Versionsnummer, Tag und Veröffentlichung (Nutzerfreigabe) und Schritt 5
(Upgrade der echten Teamdatenbank, eigene Nutzerfreigabe).

## Abnahmeschritte

Spalte „Wer“: **N** = Nutzer (eigener Rechner, Konten, Neustarts), **C** = Claude,
**X** = Codex. Der jeweils andere KI-Teilnehmer prüft die Belege gegen.

### 1. Paket am endgültigen Stand

| # | Schritt | Erwartung | Wer |
| --- | --- | --- | --- |
| 1.1 | `release.yml` per `workflow_dispatch` auf dem endgültigen `main` starten | alle drei Plattformen grün, Pakettest jedes Archivs bestanden | C oder X |
| 1.2 | Probelauf: Linux-Archiv herunterladen und SHA-256 protokollieren. Nach tatsächlicher Veröffentlichung zusätzlich mit der veröffentlichten `SHA256SUMS.txt` vergleichen | Prüfsumme dokumentiert; beim Release identisch. Der manuelle Lauf erzeugt bislang keine veröffentlichte Prüfsummendatei | C oder X |
| 1.3 | Archiv enthält `prompts/start.de.md`, `prompts/start.en.md`, `docs/claude-code.en.md`, `CHANGELOG.md` | vorhanden (prüft `check_release_package.py`) | automatisch in 1.1 |

### 2. Frisches Profil, ohne Rust und ohne SQLite-Werkzeuge

| # | Schritt | Erwartung | Wer |
| --- | --- | --- | --- |
| 2.1 | Neues Benutzerkonto oder leeres `HOME`, `PATH` ohne `cargo`/`sqlite3`; Archiv entpacken | `vmind --version` meldet `vmind 0.3.0-rc.1` (bzw. die endgültige Version); SHA-256 des Archivs protokolliert | N (Konto) oder C (isoliertes `HOME`) |
| 2.2 | `vmind init test.db`, dann `vmind doctor test.db` | Schema 7, Zustand ok; Datei hat unter Unix Rechte 0600; unter Windows gelten die Ordnerrechte | C |
| 2.3 | `vmind start-prompt` und `vmind start-prompt en` | deutscher bzw. englischer Text; `vmind start-prompt fr` scheitert mit klarer Meldung | C |
| 2.4 | Kurzer Ablauf mit synthetischem Eintrag: `add`, passende `validate`-Freigabe, `recall`, `log`, `resume`, `report`, jeweils als eigener Prozess | Einträge bleiben über Prozesse erhalten | C |
| 2.5 | `audit-secrets test.db` | Exit 0, Hinweiszeile, keine Funde | C |

### 3. Upgrade 5 → 6 und Wiederherstellung an einer Kopie

| # | Schritt | Erwartung | Wer |
| --- | --- | --- | --- |
| 3.1 | Kopie der echten `vmind.db` mit dem neuen isolierten Kandidaten über `backup` anlegen, **ohne** vorher `stats`/`resume` auf dem Original auszuführen | geprüfte Schema-5-Sicherung, Original nicht migriert; das installierte 0.2.0-Binary besitzt noch kein `backup` | C |
| 3.2 | Neues Release-Binary: `doctor` auf der Kopie | Schema 5, `migration_required: true`, Datei unverändert | C |
| 3.3 | `stats` auf der Kopie | automatische Sicherung `*.before-schema-6-*.db` entsteht, Schema danach 6, `doctor` ok | C |
| 3.4 | Zeilenzahlen und Feldinhalte aller bisherigen Tabellen vergleichen; `resume`/`recall` gegen bekannte aktuelle Ziele und Einträge prüfen | gespeicherte Daten unverändert, neue `observations` leer; neue Snapshot-Felder/Filter dürfen die Darstellung ändern, kein pauschaler Bytevergleich alter und neuer `resume`-Antworten | C, gegengeprüft von X |
| 3.5 | Automatische Sicherung zurückspielen (Kopie der Kopie), altes Binary öffnet sie | Schema 5, gleicher `resume`-Stand | C |
| 3.6 | Altes Binary auf Schema-6-Kopie | verweigert mit „Unbekannte Datenbankversion“, Datei unverändert | C |

### 4. Reale Clients

| # | Schritt | Erwartung | Wer |
| --- | --- | --- | --- |
| 4.1 | MCP-Server in Claude Code mit dem neuen Binary auf einer **Testdatenbank** neu einrichten (`docs/claude-code.en.md`), Client neu starten | Werkzeuge `describe`, `resume`, `recall`, `log` funktionieren; Datenbank wird nicht ungewollt angelegt | N (Neustart), C (Prüfung) |
| 4.2 | Beide Startsprachen getrennt in den Host-Projektanweisungen einbinden; optionalen SessionStart-Hook für `resume` prüfen | passende Startanweisung und aktueller Projektstand erscheinen; Bereich stimmt | N, C |
| 4.3 | `observe`-Hook in einer echten Sitzung | Einträge in `observations` nur mit Werkzeug/Ergebnis/Pfad; kein Befehl, keine Ausgabe in den Datei-Bytes | N, C |
| 4.4 | Codex-Anbindung über Terminal/JSONL mit neuem Binary | `messages`/`log` funktionieren; keine automatische Anbindung behauptet | X |

### 5. Upgrade der echten Teamdatenbank (eigene Freigabe)

Erst nach 1–4 und nach ausdrücklicher Freigabe durch den Nutzer:

1. Alle Clients beenden (MCP-Server beider Sitzungen, Hooks). Den laufenden MCP-Prozess
   beendet nur der Nutzer bzw. ein Neustart.
2. Mit dem isolierten neuen Kandidaten `backup vmind.db backups/vmind-vor-schema6-DATUM.db`
   und `doctor` auf der Sicherung ausführen. Das bisher installierte 0.2.0 hat diese
   Wartungsbefehle nicht; `backup` des neuen Kandidaten migriert das Original nicht.
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
