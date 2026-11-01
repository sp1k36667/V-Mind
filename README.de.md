# V-Mind

[English](README.md) · **Deutsch**

[![Rust checks](https://github.com/sp1k36667/V-Mind/actions/workflows/ci.yml/badge.svg)](https://github.com/sp1k36667/V-Mind/actions/workflows/ci.yml)
[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-blue.svg)](LICENSE)

**Der Duden für KIs: ein überprüfbares Gedächtnis, das Neustarts überlebt.**

KIs vergessen nach jeder Sitzung alles und behaupten manchmal selbstsicher Falsches.
V-Mind ist ein kleiner lokaler Speicher (Rust + SQLite), in dem eine KI zwei Dinge
dauerhaft ablegen und wiederfinden kann:

1. **Geprüftes Wissen:** gelöste Fehler und bewährte Lösungen, jeweils mit Quelle
   und Prüfnachweis. Neues Wissen ist erst *ungeprüft* und wird erst nach einer
   echten Prüfung freigegeben.
2. **Projektgedächtnis:** Ziel, Aufgaben, Entscheidungen, nächster Schritt und
   Gesprächsverlauf. So weiß eine KI auch in einer neuen Sitzung, wo die Arbeit steht.

V-Mind ist modellunabhängig. Es funktioniert als **MCP-Server** (z. B. mit Claude),
über die Kommandozeile, über ein einfaches JSONL-Protokoll und mit lokalen Modellen
über Ollama.

> Status: experimenteller Prototyp, Version 0.2.0, MIT-Lizenz. Was gebaut ist und wie es
> geprüft wurde: [Projektstand](#projektstand-was-gebaut-ist-und-wie-es-geprüft-wurde).

## Was V-Mind anders macht

Die meisten KI-Gedächtnisse speichern einfach, was die KI für wichtig hält.
V-Mind trennt dagegen streng zwischen *vermutet* und *geprüft*:

```
  propose / add            validate (Mensch/CLI, mit Nachweis)       invalidate
 ───────────────▶ pending ─────────────────────────────────▶ validated ──────────▶ invalidated
                  wird nie abgerufen                          wird abgerufen        nie mehr abgerufen,
                                                                                    Historie bleibt
```

- **Nur validiertes Wissen** wird abgerufen, immer mit Quelle, Prüfer und Nachweis.
- **Über MCP kann eine KI Wissen nur vorschlagen.** Die Freigabe ist absichtlich kein
  MCP-Werkzeug, sondern nur über die Kommandozeile oder einen Prüfbefehl möglich. Eine KI,
  die zusätzlich Shell-Befehle ausführen darf, kann auch diese Kommandozeile aufrufen;
  siehe [Vertrauen, Datenschutz und Sicherung](#vertrauen-datenschutz-und-sicherung).
- **V-Minds Befehle überschreiben nichts still.** Veraltetes wird zurückgezogen, jede
  Änderung über V-Mind bleibt in der Historie nachvollziehbar.
- **Projektbereiche** (`--scope`) halten Projekte getrennt; der Bereich `global`
  gilt für alle.
- **Alles lokal:** eine SQLite-Datei, kein Cloud-Dienst und keine GPU nötig.

**Die Idee dahinter: Lernen über Läufe, ohne Training.** Ein Modell findet über einen
echten Test einen Fehler, behebt ihn und schlägt die Erfahrung vor. Sobald die Prüfung
sie bestätigt, können spätere Läufe sie abrufen. Ob ein Modell dadurch den Fehler bei
*neuen* Aufgaben vermeidet, ist noch nicht gezeigt; unsere bisherigen Versuche fanden
keine Lernkurve (siehe unten). Was heute funktioniert: Projekte zuverlässig fortsetzen
und geprüfte Lösungen wiederverwenden.

In V-Mind wird eine gespeicherte Erfahrung erst genutzt, wenn ein Mensch oder ein
ausführbarer Prüfbefehl sie bestätigt hat; die Bestätigung bleibt am Eintrag.
[Verhältnis zu anderen Ansätzen](docs/design.md#abgrenzung-zu-ähnlichen-ansätzen).

## Wofür?

- **Programmieren mit KI:** gelöste Fehler und bewährte Lösungen dauerhaft verfügbar,
  auch für andere Modelle.
- **Lange Projekte:** Die KI weiß nach jedem Neustart, was erledigt ist und was als
  Nächstes kommt.
- **Kleine lokale Modelle zu Spezialisten machen:** ein allgemeines Modell plus
  geprüftes Fachwissen, z. B. für die Wissenschaft, mit Quellen und ohne Training.
  Das ist bisher eine Hypothese; [Chancen und Grenzen](docs/design.md#spezialisierung-kleiner-lokaler-modelle).

## Taugt es heute schon etwas? Eine ehrliche Antwort

**Ja, für eine Sache: den Projektstand einer KI über Sitzungen hinweg und zwischen
verschiedenen KI-Werkzeugen zuverlässig zu halten. Das größere Versprechen, dass eine KI
aus Erfahrung lernt, ist nicht belegt.**

Was im Alltag funktioniert, nicht nur im Test:

- **Ein Projekt nach einem Neustart fortsetzen.** Ein Start-Hook gibt der KI Ziel, offene
  Aufgaben und Entscheidungen mit, sie macht dort weiter, wo sie aufgehört hat. V-Mind wird
  selbst so entwickelt.
- **Zwei verschiedene KIs teilen sich einen Arbeitsstand.** Claude und Codex haben die
  Arbeit an V-Mind über ein V-Mind-Gespräch abgestimmt, mit fast 70 Nachrichten,
  Übergaben und gegenseitigen Prüfungen. Normalerweise wissen zwei KI-Programme nichts
  voneinander.
- **Wissen mit Herkunft.** Ein Eintrag gilt erst, wenn ein Test oder ein Mensch ihn
  bestätigt hat, und man sieht immer, wer, wann und womit.
- **Solide Grundlagen:** lokal, eine Datei, automatische Tests, geprüfte Sicherungen vor
  jedem Upgrade, fertige Programme für Linux, macOS und Windows.

Was noch fehlt:

- **Lernen ist nicht gezeigt.** Unsere Versuche fanden bei neuen Aufgaben keine Lernkurve.
- **Fortsetzung durch ein kleines lokales Modell ebenfalls nicht.** Im Test schnitt
  Gemma 4 12B mit `resume` schlechter ab als mit denselben Daten als einfache Liste; die
  Hauptursache ist behoben, der Folgetest läuft noch nicht.
- **Mitschreiben hängt noch an der KI.** Sie muss selbst daran denken einzutragen, was sie
  getan hat; ein automatisches Protokoll über einen Claude-Code-Hook ist gebaut, aber noch
  nicht gemergt.
- **Die Suche findet Wörter und Wortteile, keine Bedeutungen.**

**Kurz:** Wer mit Claude Code oder ähnlichen Werkzeugen an längeren Projekten arbeitet,
macht mit V-Mind heute schon das Fortsetzen und Übergeben zuverlässiger und
nachvollziehbarer. Ein fertiges Produkt für die breite Masse ist es noch nicht.

## Projektstand: was gebaut ist und wie es geprüft wurde

*Stand 1. November 2026.* Zu jedem Punkt steht, womit er geprüft wurde. Offene Fragen
stehen als offen da.

**Veröffentlicht: [Version 0.2.0](https://github.com/sp1k36667/V-Mind/releases/tag/v0.2.0)**
mit fertigen Programmen für Linux x86_64, macOS arm64 und Windows x86_64 samt
SHA-256-Prüfsummen. Inhalt: MCP-Server, Prüfbefehle mit `revalidate`, Teilwortsuche,
kompaktes `resume`, eingebautes SQLite. Siehe [Changelog](CHANGELOG.md).

**Auf `main` seit 0.2.0, noch nicht veröffentlicht:**

| Funktion | Was sie tut |
|---|---|
| `vmind doctor DB` | Prüft Schema, Integrität, Fremdschlüssel und nötige Tabellen, nur lesend |
| `vmind backup DB ZIEL` | Geprüfte SQLite-Sicherung, die nie eine vorhandene Datei überschreibt |
| Automatische Sicherung vor Upgrades | Jede Schemaumstellung schreibt und prüft zuerst eine Sicherung; scheitert sie, bleibt alles unverändert |
| `vmind report DB` | Lesbarer Bericht in Markdown für Menschen; strikt nur lesend, geprüftes Wissen und ungeprüfte Vorschläge getrennt |
| Aufgeräumtes `resume` | Überholte Ziele, nächste Schritte und Aufgabenstände erscheinen nicht mehr neben den aktuellen |
| Optionale Werkzeugbeobachtung (Schema 6) | Claude-Code-Hook meldet Werkzeug, Ergebnis und begrenzte relative Projektpfade; keine Inhalte, Befehle oder Ausgaben |
| Dateischutz | Neue Datenbanken erhalten unter Unix Modus 0600; URI-artige Dateinamen werden wörtlich behandelt |
| Verständliche Fehler | Ungültige Zustände erhalten erklärende Meldungen |
| Sichtbarer Prüfzustand | Wissensabruf zeigt letzte Prüfung der aktiven Definition samt Zeit; Fehler verdecken keinen früheren Fehlbefund |

**Automatische Tests:** 96 Tests laufen bei jeder Änderung in GitHub Actions unter Linux,
zusammen mit Clippy (jede Warnung ist ein Fehler) und einer Formatprüfung; die Builds für
macOS und Windows werden ebenfalls geprüft; dort laufen zusätzlich die Dateipfad-/Sicherungstests. Abgedeckt sind unter anderem:

- Upgrades älterer Schemas ohne Datenverlust; fehlgeschlagene Upgrades lassen die
  Datenbank unverändert;
- Sicherungen überschreiben nie, und eine fehlgeschlagene automatische Sicherung
  verhindert das Upgrade;
- 16 getrennte Prozesse schreiben gleichzeitig, ohne dass ein Eintrag verloren geht;
- Prüfbefehle: keine Shell, Zeitlimit auch beim Lesen der Ausgabe, Zeitüberschreitung
  oder Fehler bestätigen nie einen Eintrag;
- Bereichs- und Statusfilter in allen Suchwegen, auch in der Teilwortsuche;
- MCP- und JSONL-Protokoll, auch mit kaputten und übergroßen Eingaben;
- `report` lässt die Datenbank Byte für Byte unverändert, auch bei älterem Schema.

**Von Hand geprüft:** der veröffentlichte Linux-Download (Prüfsumme und erster Start); das
Upgrade einer echten Projektdatenbank von Schema 4 auf 5 mit geprüfter Sicherung,
Integritätsprüfung und gleichen Zeilenzahlen; die Installation aus dem Release auf einem
frischen Benutzerprofil ohne Rust- oder SQLite-Werkzeuge.

**Testliste: alle Versuche, durchgeführt und geplant** (Einzelheiten unten, alle Rohdaten
im Repository):

| # | Frage | Modell | Stand | Ergebnis |
|---|---|---|---|---|
| 1 | Hilft eine gespeicherte, geprüfte Lösung einem kleinen Modell? | Gemma 4 E2B | durchgeführt | Ja beim Wiederverwenden derselben Lösung (7/7 statt 2/7 Prüfungen); sagt nichts über Lernen. [Bericht](docs/experiments/e2b-pilot.md) |
| 2 | Wird ein Modell durch eigene geprüfte Lehren besser? | Gemma 4 E2B | durchgeführt, vorab geplant | Keine Lernkurve; 0 von 108 Aufgabenläufen gelöst; etwa jede fünfte ungeprüfte Lehre eindeutig falsch. [Bericht](docs/experiments/lernkurve.md) |
| 3 | Gleiche Frage wie 2 | Gemma 4 12B | durchgeführt, explorativ | Ebenfalls keine Lernkurve, aber 12B behob Fehler selbst, und seine ungeprüften Lehren waren selten falsch. [Bericht](docs/experiments/lernkurve.md#explorativer-lauf-mit-gemma-4-12b) |
| 4 | Kann eine frische Sitzung ein Projekt aus `resume` fortsetzen? | Gemma 4 12B | durchgeführt, vorab geplant | Kriterien verfehlt: 117/165 gegen 133/165 für dieselben Daten als flache Liste; Ursache gefunden und behoben. [Bericht](docs/experiments/continuity-pilot.md) |
| 5 | Hilft die Korrektur, und spielt das Format eine Rolle? | Gemma 4 12B | durchgeführt, 80 vorab geplante Aufrufe | Alte nächste Schritte: JSON 1→0, Text 2→0 (von je 15); Gesamtgenauigkeit steigt nicht. [Bericht](docs/experiments/continuity-2x2.md) |
| 6 | Hilft eine richtige, geprüfte Lehre bei *neuen* Aufgaben? | Gemma 4 12B | Entwurf | – [Entwurf](docs/experiments/transfer-pilot-plan.md) |
| 7 | Findet `recall` das Richtige und hält es Bereichs- und Statusgrenzen ein? | kein Modell | durchgeführt, vorab geplant, synthetischer Korpus | Grenzen ohne Ausnahme gehalten; wortgleiche Fragen 10/10 auf Platz 1; längere gebeugte Formen 0/5 erkannt; im Mittel 2,6 unpassende Treffer je Frage. [Bericht](docs/experiments/abruf-korpus.md) |

Neue Versuche laufen **nur noch mit Gemma 4 12B**. In den Versuchen 2 und 3 hat 12B seine
Fehler viel öfter selbst behoben und viel seltener falsche Lehren geschrieben als E2B; es ist
damit die bessere Grundlage, um zu prüfen, ob Lehren überhaupt helfen. Versuch 6 beginnt mit
einer von Hand geschriebenen, richtigen Lehre: Hilft selbst die nicht, können selbst
geschriebene Lehren nicht die Lösung sein.

**In Arbeit:** vollständigere Downloadpakete und weitere Betriebs-/Datenschutzabnahme. Die echte Datenbank verwendet weiterhin Schema 5;
Schema 6 ist bislang an isolierten Datenbanken geprüft.
[Offene Pull Requests](https://github.com/sp1k36667/V-Mind/pulls).

**Wie entwickelt wird:** Der Projektinhaber legt Ziele und Prioritäten fest. Zwei
KI-Assistenten, Claude (Anthropic) und Codex (OpenAI), schreiben und prüfen den Code. Immer
nur einer schreibt Code; der andere prüft jede Änderung und rechnet berichtete Zahlen
unabhängig nach. Abgestimmt wird über ein V-Mind-Gespräch – V-Mind wird also mit V-Mind
gebaut.

## In Claude nutzen (Claude Desktop / Claude Code)

Mit V-Mind als MCP-Server liest Claude beim Start den Projektstand, sucht vor
Änderungen nach geprüftem Wissen und hält erledigte Arbeit im Tagebuch fest.
Das funktioniert im **Code-Tab der Claude-Desktop-App** und in **Claude Code im
Terminal**.

### 1. V-Mind installieren

**Weg A: herunterladen.** Fertige Programme für Linux, macOS und Windows gibt es auf der
[Release-Seite](https://github.com/sp1k36667/V-Mind/releases). Entpacken und `vmind`
(unter Windows `vmind.exe`) in einen Ordner im `PATH` legen. SQLite ist eingebaut, sonst
wird nichts gebraucht. `SHA256SUMS.txt` enthält die Prüfsummen. Die Programme sind nicht
signiert; unter macOS muss man sie einmal mit `xattr -d com.apple.quarantine vmind` erlauben.

**Weg B: selbst bauen.** Voraussetzungen: Rust/Cargo, Git und ein C-Compiler (SQLite wird
mitgebaut). Unter Ubuntu `sudo apt install build-essential`, dann:

```sh
git clone https://github.com/sp1k36667/V-Mind.git
```

```sh
cargo install --path V-Mind/crates/vmind-cli --locked
```

Danach steht der Befehl `vmind` zur Verfügung (`vmind --help` zeigt alle Befehle).

### 2. Datenbank in deinem Projekt anlegen

Im Ordner des Projekts, an dem Claude arbeiten soll:

```sh
vmind init vmind.db
```

Die Datenbank ist lokal und gehört nicht ins Git-Repository (`*.db` in `.gitignore`).

### 3. MCP-Server eintragen

Lege im Projektordner eine Datei `.mcp.json` an. Ersetze `mein-projekt` durch einen
Namen für den Projektbereich:

```json
{
  "mcpServers": {
    "vmind": {
      "command": "vmind",
      "args": ["--scope", "mein-projekt", "mcp", "vmind.db"]
    }
  }
}
```

Alternativ mit der Claude-Code-Kommandozeile, nur für dich und dieses Projekt:

```sh
claude mcp add vmind -- vmind --scope mein-projekt mcp vmind.db
```

### 4. Claude neu starten und Server freigeben

Beim nächsten Start einer Sitzung im Projekt fragt Claude, ob der Server `vmind`
erlaubt werden soll. Danach hat Claude diese Werkzeuge:

| Werkzeug | Zweck |
|---|---|
| `resume` | Projektstand laden: Ziel, Aufgaben, Entscheidungen, nächster Schritt |
| `recall` | Geprüftes Wissen per Volltextsuche finden |
| `get` | Einen Eintrag mit vollständiger Historie ansehen |
| `propose` | Neue Erfahrung als *ungeprüft* vorschlagen |
| `log` | Aufgabe, Entscheidung, nächsten Schritt oder Notiz festhalten |
| `journal` | Projekttagebuch seitenweise lesen |
| `pending`, `stats` | Ungeprüfte Einträge und Zahlen anzeigen |
| `session_new`, `sessions`, `message`, `messages` | Gespräche speichern und lesen |

**Claude-Desktop-App, Chat (außerhalb des Code-Tabs):** Chats lesen keine `.mcp.json`.
Den Server in `claude_desktop_config.json` eintragen (Einstellungen → Entwickler →
Konfiguration bearbeiten; unter macOS `~/Library/Application Support/Claude/`, unter
Windows `%APPDATA%\Claude\`) und **absolute Pfade** verwenden, weil die App nicht im
Projektordner startet. Das ist ein manuelles Beispiel, noch nicht auf allen Plattformen
getestet:

```json
{
  "mcpServers": {
    "vmind": {
      "command": "/absoluter/pfad/zu/vmind",
      "args": ["--scope", "mein-projekt", "mcp", "/absoluter/pfad/zum/projekt/vmind.db"]
    }
  }
}
```

**Einrichtung prüfen.** Im Terminal im Projektordner:

```sh
vmind --scope mein-projekt stats vmind.db
```

Das zeigt Schemaversion und Zahlen. Wenn Claude die `vmind`-Werkzeuge nicht anzeigt:

| Anzeichen | Wahrscheinliche Ursache und Abhilfe |
|---|---|
| Server startet nicht, „command not found“ | `vmind` liegt nicht im `PATH` der App. Absoluten Programmpfad bei `command` eintragen. |
| Server startet nicht, Datenbank nicht gefunden | Der Server öffnet nur eine vorhandene Datenbank und legt keine an, nur weil ein Pfad vertippt ist. Der Pfad in `args` bezieht sich auf den Ordner, in dem die App startet. Absoluten Pfad verwenden oder dort zuerst `vmind init` ausführen. |
| Keine Freigabeabfrage in Claude Code | Zustand mit `/mcp` prüfen; wurde der Projektserver abgelehnt, mit `claude mcp reset-project-choices` die Projektentscheidungen zurücksetzen und eine neue Sitzung starten. Siehe [offizielle Claude-Code-Dokumentation](https://code.claude.com/docs/en/mcp). |
| Altes Verhalten nach einem Update | Ein laufender MCP-Server behält das alte Programm bis zum Neustart von Claude. Nach der Installation einer neuen Version Claude neu starten. |

### 5. Optional: Projektstand automatisch laden

Ein SessionStart-Hook gibt Claude den Projektstand schon beim Sitzungsstart mit,
ohne dass Claude erst daran denken muss. Datei `.claude/settings.local.json` im
Projektordner (persönlich, nicht ins Repository einchecken):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "vmind --scope mein-projekt resume \"$CLAUDE_PROJECT_DIR/vmind.db\""
          }
        ]
      }
    ]
  }
}
```

Entwicklungsstand nach 0.2.0 (Schema 6): Claude Code kann zusätzlich jeden Bash-, Edit-
und Write-Aufruf über einen `PostToolUse`-Hook an `vmind observe` melden. V-Mind behält
nur Werkzeug, ob es abgeschlossen oder fehlgeschlagen ist, und den Dateipfad relativ zum
Projekt; nie Befehle, Ausgaben, Fehlertexte oder Dateiinhalte. `resume` zeigt die letzten
drei Sitzungen zusammengefasst, als beobachtet und nicht geprüft markiert. Einrichtung
und Grenzen: [docs/cli.md](docs/cli.md#beobachtungen-aus-claude-code-ab-schema-6).

### 6. Loslegen

Sag Claude zum Beispiel:

- „Lies den Projektstand aus V-Mind und mach beim nächsten Schritt weiter.“
- „Halte in V-Mind fest, was du erledigt hast, mit dem Testergebnis als Nachweis.“
- „Schlag die Lösung für diesen Fehler in V-Mind als ungeprüften Eintrag vor.“

Geprüftes Wissen gibst du selbst frei, nachdem du die Lösung wirklich getestet hast:

```sh
vmind pending vmind.db
```

```sh
vmind validate vmind.db 1 'Dein Name' 'Welcher Test lief und mit welchem Ergebnis'
```

Oder du lässt einen echten Test entscheiden, siehe nächster Abschnitt.

Wo das Projekt steht, ohne eine KI zu fragen: `vmind --scope mein-projekt report
vmind.db` gibt einen lesbaren Bericht in Markdown aus: Ziel, nächster Schritt, Aufgaben,
letzte Entscheidungen, geprüftes Wissen mit letztem Prüflauf und getrennt davon
ungeprüfte Vorschläge (Entwicklungsstand nach 0.2.0).

### Prüfbefehle: Tests entscheiden, was gilt

Ein Eintrag kann einen **Prüfbefehl** bekommen, zum Beispiel den Test, der den Fehler
gefunden hat. Besteht er, wird ein ungeprüfter Eintrag automatisch gültig, mit Befehl,
Exit-Code und Laufzeit als Nachweis. Das ist der Kern der Lernschleife: Die KI schlägt
vor, der Test entscheidet.

```sh
vmind check-set vmind.db 1 'Dein Name' . pytest tests/test_app.py -k corrupt
```

```sh
vmind check vmind.db 1
```

`revalidate` führt alle Prüfbefehle des Bereichs erneut aus, zum Beispiel nach einem
Update. Fällt ein gültiger Eintrag durch, wird das gemeldet. Zurückgezogen wird er nur
mit `--invalidate`, weil ein Rückzug endgültig ist:

```sh
vmind --scope mein-projekt revalidate vmind.db
```

Sicherheit: Prüfbefehle laufen ohne Shell (keine `;`, `&&`, Umleitungen) in einem festen
Ordner und mit Zeitlimit. Setzen und Ausführen geht **nur über die Kommandozeile**,
nicht über MCP. Eine KI, die nur die MCP-Werkzeuge hat, kann V-Mind also keinen Befehl
unterschieben. Lies einen Prüfbefehl vor dem Setzen wie jeden Befehl, den du ausführst.
Achte darauf, dass
der Befehl wirklich etwas prüft: `cargo test` mit einem vertippten Testnamen führt null
Tests aus und meldet trotzdem Erfolg. Details: [docs/cli.md](docs/cli.md#prüfbefehle).

Für andere MCP-fähige Programme gilt dasselbe: Server-Befehl
`vmind --scope BEREICH mcp /absoluter/pfad/vmind.db`. Wo die Konfiguration liegt,
hängt vom jeweiligen Programm ab. Technische Details: [docs/protocol.md](docs/protocol.md).

## Weitere Wege, V-Mind zu nutzen

**Kommandozeile:** Wissen speichern, prüfen, abrufen und das Projekttagebuch führen.

```sh
vmind --scope mein-projekt recall vmind.db 'SQLite Migration'
```

```sh
vmind --scope mein-projekt task vmind.db datenbank done 'Migration implementiert' 'cargo test: alle Tests bestanden'
```

**Lokale Modelle über Ollama:** `ask` ruft passendes Wissen und den Projektstand ab
und stellt die Frage an ein lokales Modell (Standard: Gemma 4 E2B, siehe
`setup/Modelfile`). Antworten werden gespeichert, aber nie automatisch als Wissen
übernommen.

```sh
vmind --scope mein-projekt ask vmind.db 'Wie verhindere ich fehlende Tabellen beim ersten Start?'
```

**JSONL-Protokoll:** `vmind serve vmind.db` verarbeitet ein JSON-Objekt pro Zeile
über stdin/stdout, für eigene Programme ohne MCP. Siehe [docs/protocol.md](docs/protocol.md).

Alle Befehle, der Ablauf für lange Projekte, Konfiguration und Grenzen stehen
ausführlich in **[docs/cli.md](docs/cli.md)**.

## Erster Versuch: hilft geprüftes Wissen einem kleinen Modell?

Das kleine lokale Modell Gemma 4 E2B sollte einen Python-Aufgabenplaner bauen,
einmal ohne und einmal mit V-Mind. Im Speicher lag eine zuvor von Gemma 4 12B
erzeugte und geprüfte Lösung. Aufgabe, Einstellungen und Prüfungen waren gleich.

| Ergebnis | Ohne V-Mind | Mit V-Mind |
|---|---:|---:|
| Unabhängige Funktionsprüfungen | 2 von 7 | 7 von 7 |
| Eigene Testsuite am Ende | nicht lauffähig | 10 von 10 |
| Modellzeit, zwei Versuche zusammen | 46,5 s | 17,1 s |

**Ehrliche Einordnung:** Das zeigt, dass ein kleines Modell eine gespeicherte,
geprüfte Lösung zuverlässig wiederverwenden kann. Die Ausgabe war bytegleich mit
der Referenz. Es zeigt *nicht*, dass das Modell dazulernt oder neue Aufgaben löst.
[Aufbau, Messwerte und Grenzen im Detail](docs/experiments/e2b-pilot.md).

## Zweiter Versuch: Wird ein Modell durch eigene geprüfte Lehren besser?

Über sechs *verschiedene* Aufgaben hinweg speicherte das Modell behobene Fehler als
Lehren. In Bedingung B zählte eine Lehre erst nach bestandener Prüfung, in C ungeprüft.
**Ergebnis: keine Lernkurve.** Gemma 4 E2B (vorab geplant) löste keinen der 108
Aufgabenläufe; die Hypothesen werden nicht gestützt. Gemma 4 12B (explorativ) löste
einige Aufgaben, wurde durch geprüfte Lehren aber ebenfalls nicht besser.

Gezeigt haben die Läufe: Ungeprüftes Gedächtnis sammelt bei einem schwachen Modell
falsche Lehren (in einer E2B-Stichprobe etwa jede fünfte eindeutig falsch), und die
Bestätigung über „die Prüfung, die vorher fehlschlug, besteht jetzt“ ist zu grob, weil
ein Fix oft viele Prüfungen gleichzeitig umschaltet. Ein kleinerer Folgeversuch, der den
Transfer einer einzelnen geprüften Lehre misst, ist entworfen, aber nicht gelaufen.
[Bericht](docs/experiments/lernkurve.md), [Entwurf Folgeversuch](docs/experiments/transfer-pilot-plan.md).

## Dritter Versuch: Kann eine frische Sitzung ein Projekt fortsetzen?

Das prüft, wofür V-Mind vor allem gedacht ist. Gemma 4 12B beantwortete elf feste Fragen
zu drei synthetischen Projekten (aktuelles Ziel, Aufgabenstände, die ersetzte
Backend-Entscheidung, der nächste Schritt, zwei Fragen ohne Antwort in den Daten), in 45
vorab festgelegten Läufen: ohne Verlauf, mit denselben Daten als flache Feldliste und mit
der `resume`-Ausgabe von V-Mind.

| | Ohne Verlauf | Flache Liste | V-Mind `resume` |
|---|---:|---:|---:|
| Richtige Antworten (streng, von 165) | 6 | 133 | 117 |

**Ergebnis: Die vorab festgelegten Kriterien wurden verfehlt**, und das Ergebnis ist
unverändert veröffentlicht. Die Nachprüfung der Rohantworten zeigt, woher die 16 Punkte
kommen: 7 waren echte Fehler, weil `resume` alte „nächste Schritte“ neben dem aktuellen
zeigte und das Modell manchmal einen alten nannte; der größte Rest waren richtige Fakten in
falscher Form (ein Ordner mit Satzpunkt, „Backend SQLite“ statt „SQLite“). Die alten
Einträge filtert `resume` inzwischen heraus. Der vorab geplante 2×2-Folgelauf mit 80 neuen Aufrufen ist abgeschlossen: Bekannte
überholte nächste Schritte fallen in JSON/Text von 1/2 auf 0/0. Die Gesamtgenauigkeit
steigt dabei nicht (159→156 und 152→144 richtige verfügbare Fakten von je 160).
Mehrdeutige Fragen nach einer „Kennung“ führten oft zur Datensatz-ID statt zum erwarteten
Text. Der Bericht behält die ursprüngliche Wertung bei; keine allgemeine Lernwirkung.
[Bericht](docs/experiments/continuity-pilot.md),
[Bericht und Grenzen des Folgeversuchs](docs/experiments/continuity-2x2.md).

## Vertrauen, Datenschutz und Sicherung

**Was V-Mind zusichert:** Nur als *validiert* markierte Einträge werden abgerufen. Jede
Validierung, jeder Rückzug und jeder Prüflauf über V-Mind wird mit wer, wann und welchem
Nachweis festgehalten. V-Minds Befehle überschreiben nichts still. Eine fehlgeschlagene
Migration lässt die Datenbank unverändert. Das gilt für V-Minds eigene Befehle; ein
Programm, das direkt in die SQLite-Datei schreibt, umgeht diese Zusagen, und die Historie
selbst ist nicht fälschungssicher.

**Was V-Mind nicht zusichert:**

- **Validierung ist nachvollziehbar, nicht fälschungssicher.** Die MCP-Werkzeuge können
  nicht validieren. Jedes Programm und jede KI, die auf deinem Rechner Shell-Befehle
  ausführen oder Dateien schreiben darf, kann aber `vmind validate` aufrufen oder die
  SQLite-Datei direkt ändern. Arbeitet eine KI mit Shell-Zugriff, zeigt die Historie, was
  passiert ist; verhindern kann sie es nicht.
- **Ein bestandener Prüfbefehl bestätigt, was er prüft**, nicht, dass die Erklärung im
  Eintrag stimmt. In unseren Versuchen gab es Lehren mit falscher Begründung, deren
  Prüfung trotzdem bestand.
- **Projektbereiche sind keine Zugriffskontrolle.** Wer die Datei lesen kann, liest alle
  Bereiche.

**Datenschutz:** Alles liegt unverschlüsselt in einer lokalen SQLite-Datei: Wissen,
Projekttagebuch und Gespräche. Der Speicher bleibt auf deinem Rechner. `ask` schickt Frage
und abgerufenen Kontext an den Ollama-Endpunkt in `VMIND_OLLAMA_URL` (standardmäßig ein
lokaler Server; jede andere eingestellte Adresse erhält diese Daten). MCP-Clients geben,
was sie aus V-Mind lesen, an ihr Modell weiter, das in der Cloud laufen kann. Ab dem
Entwicklungsstand nach 0.2.0 wird eine neue Datenbankdatei unter Linux und macOS nur für
den Besitzer lesbar angelegt (0600); vorhandene Dateien behalten ihre Rechte, unter
Windows gelten die Rechte des Ordners. Keine Passwörter oder Schlüssel speichern. Einen
Befehl zum Löschen von Inhalten gibt es derzeit nicht; ist ein Geheimnis in der Datei
gelandet, ein früheres Backup zurückspielen oder es mit SQLite-Werkzeugen entfernen und
das Geheimnis als offengelegt behandeln.

**Sicherung und Upgrade:** Die Datenbank ist eine Datei; während geschrieben wird, legt
SQLite daneben vorübergehend `-journal`- (oder `-wal`/`-shm`-)Dateien an. Die Datei nur
kopieren, wenn kein Client läuft, oder mit SQLite sichern, das jederzeit eine
konsistente Kopie erstellt:

```sh
sqlite3 vmind.db ".backup vmind-sicherung.db"
```

Vor dem Installieren einer neuen Version sichern und alle Clients, die die Datenbank
nutzen, beenden oder neu starten (MCP-Server laufen sonst mit dem alten Programm weiter).
Die neue Version stellt die Datenbank beim ersten Zugriff um; der
[Changelog](CHANGELOG.md) nennt Schemaänderungen. Der Entwicklungsstand nach 0.2.0 ergänzt
`vmind backup` (geprüft, überschreibt nie), `vmind doctor` (prüft nur lesend) und eine
automatische geprüfte Sicherung vor jeder Schemaumstellung; siehe
[docs/operations.md](docs/operations.md).

## Grenzen

- Die Suche (SQLite FTS5) findet ganze Wörter und Wortteile (z. B. „Filter“ in
  „Testfilter“), aber keine Bedeutungen: keine Synonyme und keine Übersetzung.
- `resume` zeigt einen begrenzten Ausschnitt (offene Aufgaben, die letzten Entscheidungen
  und Ereignisse). Ältere Details bleiben im Tagebuch und müssen mit `journal` gelesen
  werden.
- Eine Lernwirkung ist nicht belegt; siehe die Versuche oben.
- Keine automatische Anbindung an Codex oder ChatGPT; V-Mind beobachtet keine
  anderen Programme.

Vollständige Liste: [docs/cli.md](docs/cli.md#konfiguration-und-grenzen).

## Projekt

| Datei | Inhalt |
|---|---|
| [docs/cli.md](docs/cli.md) | Alle Befehle, lange Projekte, Konfiguration, Entwicklung |
| [docs/protocol.md](docs/protocol.md) | JSONL-Protokoll und MCP-Server |
| [docs/design.md](docs/design.md) | Architektur und Entscheidungen |
| [docs/start-prompt.md](docs/start-prompt.md) | Startanweisung für KI-Clients |
| [AGENTS.md](AGENTS.md) | Arbeitsregeln für KIs, die an V-Mind selbst arbeiten |
| [CHANGELOG.md](CHANGELOG.md) | Änderungen je Version (Englisch) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Beiträge und Prüfungen |

Aufbau: `crates/vmind-core` (SQLite-Speicher und Abruf, ohne Modellbezug) und
`crates/vmind-cli` (Kommandozeile, JSONL, MCP, Ollama-Adapter).

Prüfungen vor jedem Beitrag, jeweils einzeln:

```sh
cargo test --workspace --locked
```

```sh
cargo clippy --workspace --all-targets --locked -- -D warnings
```

```sh
cargo fmt --all -- --check
```

## Lizenz

MIT, siehe [LICENSE](LICENSE).
