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

> Status: experimenteller Prototyp. 59 automatische Tests, MIT-Lizenz.

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
- **Eine KI kann Wissen nur vorschlagen.** Die Freigabe ist absichtlich nicht über
  KI-Werkzeuge möglich, nur über die Kommandozeile.
- **Nichts wird still überschrieben.** Veraltetes wird zurückgezogen, jede Änderung
  bleibt in der Historie nachvollziehbar.
- **Projektbereiche** (`--scope`) halten Projekte getrennt; der Bereich `global`
  gilt für alle.
- **Alles lokal:** eine SQLite-Datei, kein Cloud-Dienst, keine GPU nötig.

**Die Idee dahinter: Lernen über Läufe, ohne Training.** Ein Modell findet über einen
echten Test einen Fehler, behebt ihn und schlägt die Erfahrung vor. Sobald die Prüfung
sie bestätigt, nutzen alle späteren Läufe sie und machen den Fehler gar nicht erst.

Ähnliche Ansätze wie Reflexion, Voyager oder mem0 speichern meist, was das Modell
*glaubt*. V-Mind speichert, was *nachweislich funktioniert hat*.
[Abgrenzung im Detail](docs/design.md#abgrenzung-zu-ähnlichen-ansätzen).

## Wofür?

- **Programmieren mit KI:** gelöste Fehler und bewährte Lösungen dauerhaft verfügbar,
  auch für andere Modelle.
- **Lange Projekte:** Die KI weiß nach jedem Neustart, was erledigt ist und was als
  Nächstes kommt.
- **Kleine lokale Modelle zu Spezialisten machen:** ein allgemeines Modell plus
  geprüftes Fachwissen, z. B. für die Wissenschaft, mit Quellen und ohne Training.
  Das ist bisher eine Hypothese; [Chancen und Grenzen](docs/design.md#spezialisierung-kleiner-lokaler-modelle).

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
nicht über MCP. Eine KI kann V-Mind also keinen Befehl unterschieben. Achte darauf, dass
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

## Grenzen

- Die Suche (SQLite FTS5) findet ganze Wörter und Wortteile (z. B. „Filter“ in
  „Testfilter“), aber keine Bedeutungen: keine Synonyme und keine Übersetzung.
- Eine Validierung dokumentiert eine Prüfung; V-Mind beweist nicht selbst, dass
  eine Lösung stimmt.
- Projektbereiche ordnen Wissen, sind aber keine Zugriffskontrolle. Daten liegen
  unverschlüsselt in einer lokalen Datei.
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
