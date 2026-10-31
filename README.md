# V-Mind

Ein schlanker, modellunabhängiger „Duden für KIs“: Erfahrungen dauerhaft speichern,
nachvollziehbar prüfen und im passenden Kontext wiederfinden.

Status: experimenteller Prototyp, MIT-Lizenz.

## Was jetzt funktioniert

- Rust-Workspace mit unabhängigem SQLite-Kern und Kommandozeile.
- Fehler/Lösungs-Paare und Langzeitwissen mit Quelle, Prüfer und Prüfnachweis.
- Lebenszyklus: ungeprüft → validiert → bei Bedarf zurückgezogen.
- Nachvollziehbare Ereignishistorie; Zurückziehen löscht den Eintrag nicht.
- Persistentes Projekttagebuch mit Zielen, Aufgabenständen, Entscheidungen und nächsten Schritten.
- Gespeicherte Gespräche und automatisch geladener Fortsetzungsstand für `ask`/`chat`.
- SQLite FTS5 mit BM25-Relevanzsortierung, Unicode-Suche und deutschen/englischen Stoppwörtern.
- Projektbereiche: Abruf aus dem gewählten Bereich plus dem gemeinsamen Bereich `global`.
- JSON-Ausgaben und ein modellunabhängiges JSONL-Werkzeugprotokoll über stdin/stdout.
- Optionaler lokaler Ollama-Adapter: Frage → Wissensabruf → Modellantwort.
- Atomare Migration bis Schema 3, ohne bestehende Einträge zu löschen.

Eine gespeicherte Validierung dokumentiert eine externe Prüfung. V-Mind beweist
nicht selbst, dass die Lösung richtig ist. Modellantworten sind weiterhin ungeprüft
und werden als Gesprächsverlauf gespeichert. Sie werden nicht automatisch als Fachwissen übernommen oder validiert.

## Startprompt für die nutzende KI

Die vollständige gemeinsame Startanweisung liegt in `prompts/start.de.md`.
Der Ollama-Adapter verwendet genau diese Datei als Systemprompt. Änderungen daran
werden beim nächsten Build bzw. erneuten Installieren übernommen.

```sh
vmind start-prompt
```

Für externe KI-Clients die Anweisung als Startkonfiguration übernehmen und zusätzlich
die realen Werkzeuge, Datenbank, Projektbereich und Gesprächs-ID anbinden. Der Prompt
richtet keine Verbindung ein. Details: [docs/start-prompt.md](docs/start-prompt.md).

## Voraussetzungen

Rust/Cargo, Git und die SQLite-Entwicklungsbibliothek mit FTS5; unter Ubuntu typischerweise
`build-essential`, `pkg-config` und `libsqlite3-dev`. Auf dem Entwicklungs-PC sind
Build und Tests bereits erfolgreich ausgeführt worden. Zum Wissensabruf braucht
V-Mind weder Ollama noch eine GPU. Nur `ask` benötigt einen erreichbaren Ollama-Dienst.

Gemma 4 E2B ist das erste Testmodell, keine Voraussetzung für den Speicherkern.
`setup/Modelfile` definiert `vmind-gemma4:e2b` mit 8.192 Kontext-Tokens.

## Starten

Jeden Befehl einzeln im Projektordner ausführen. Zuerst eine Datenbank initialisieren:

```sh
cargo run -p vmind-cli --locked -- init vmind.db
```

Eine Erfahrung im Projektbereich speichern:

```sh
cargo run -p vmind-cli --locked -- --scope beispiel add vmind.db error_solution 'Tabelle fehlt nach dem ersten Start' 'Migration vor dem ersten Zugriff ausführen' 'Eigener reproduzierbarer Fehlerfall'
```

Die ID aus der Ausgabe verwenden. Eintrag 1 ist hier nur ein Beispiel:

```sh
cargo run -p vmind-cli --locked -- show vmind.db 1
```

Nach tatsächlicher Prüfung mit Nachweis freigeben:

```sh
cargo run -p vmind-cli --locked -- validate vmind.db 1 'Name des Prüfers' 'Beschreibung des ausgeführten Tests und seines Ergebnisses'
```

Wissen ohne Sprachmodell abrufen:

```sh
cargo run -p vmind-cli --locked -- --scope beispiel recall vmind.db 'Tabelle erster Start Migration'
```

Oder eine Frage mit automatisch abgerufenem Wissen an Ollama stellen:

```sh
cargo run -p vmind-cli --locked -- --scope beispiel ask vmind.db 'Wie verhindere ich fehlende Tabellen beim ersten Start?'
```

Die alte Form `ask DB SUCHTEXT FRAGE` bleibt verfügbar, wenn gezielte Suchbegriffe
besser passen als die Frage selbst. `search DB SUCHTEXT` bleibt als wörtliche,
groß-/kleinschreibungssensitive Suche nur im Bereich `global` erhalten.

Einen widerlegten oder veralteten Eintrag zurückziehen:

```sh
cargo run -p vmind-cli --locked -- invalidate vmind.db 1 'Name des Prüfers' 'Konkreter Grund für das Zurückziehen'
```

Zurückgezogene Einträge werden nie mehr automatisch abgerufen und können nicht
erneut validiert werden. Korrekturen als neuen Eintrag mit Verweis auf die alte ID
in der Quelle speichern, prüfen und freigeben.

`pending DB` zeigt maximal 100 aktive ungeprüfte Einträge. `stats DB` zeigt den
Status des gewählten Bereichs plus `global`. `--json` vor dem Befehl liefert
maschinenlesbare Ausgaben. `--help` zeigt alle Befehle. `init` darf eine neue Datei
anlegen; andere Befehle verlangen eine vorhandene Datenbank.

## Direktes Programm installieren

```sh
cargo install --path crates/vmind-cli --locked
```

Nach der Installation kann jeder Aufruf auch direkt
mit `vmind` beginnen, beispielsweise `vmind stats vmind.db`. Nach Quellcodeänderungen
erneut installieren, damit das installierte Programm dem neuen Stand entspricht.
Für weitere Entwicklungssitzungen stehen Hinweise in `AGENTS.md`.

## Lange Projekte und Neustarts

`ask` speichert die Nutzerfrage vor dem Modellaufruf und danach die erfolgreiche
Antwort. Bei einem Fehler bleibt die Frage mit einem Fehlerhinweis erhalten; eine
KI-Antwort wird nicht erfunden. Weitere `ask`-Aufrufe im selben Bereich verwenden
das gleiche Standardgespräch – auch nach einem Programm- oder Rechnerneustart,
sofern dieselbe Datenbank vorhanden ist.

Das Projekttagebuch hält zusätzlich fest, was gemacht wurde und warum. Beispiele:

```sh
vmind --scope v-mind log vmind.db goal 'Ein dauerhaftes Projektgedächtnis bauen' 'Nutzeranforderung'
```

```sh
vmind --scope v-mind task vmind.db datenbank in_progress 'Migration implementieren' 'Arbeitsbericht'
```

```sh
vmind --scope v-mind task vmind.db datenbank done 'Migration implementiert und Tests ausgeführt' 'Konkreter Testlauf und Ergebnis'
```

Der gleiche Aufgabenschlüssel aktualisiert den abgeleiteten aktuellen Stand,
aber jede frühere Meldung bleibt erhalten. Statuswerte: `open`, `in_progress`,
`done`, `blocked`. Weitere Ereignistypen: `goal`, `decision`, `next_step`, `note`.
Nur tatsächlich erledigte und überprüfte Arbeit entsprechend kennzeichnen.

Beim Fortsetzen zuerst:

```sh
vmind --scope v-mind resume vmind.db
```

Die Übersicht enthält das aktuelle Ziel, den nächsten Schritt, höchstens 20 aktuelle
Aufgabenstände (unerledigte zuerst), zehn Entscheidungen, zehn letzte Projektereignisse
und zehn letzte Chatnachrichten. Gesamtzahlen zeigen, ob weitere Daten vorhanden sind.
Die vollständige Historie bleibt seitenweise verfügbar, jeweils maximal 100 Einträge:

```sh
vmind --scope v-mind journal vmind.db
```

Für die nächste Seite die letzte ausgegebene Ereignis-ID als weiteres Argument
angeben. Dasselbe Cursorverfahren gilt für `messages DB GESPRÄCH_ID [NACH_ID]`.
Eine Übersicht allein enthält also nicht jede Zeile eines monatelangen Projekts.

Mit `session-new DB TITEL` ein separates Gespräch anlegen, mit `chat DB ID FRAGE`
fortsetzen. `sessions DB` zeigt die letzten 100 Gespräche des Bereichs. Explizite
Gespräche benötigen den passenden Projektbereich bei `chat` und `resume`.

Projektkontext wird exakt nach Bereich getrennt; `global` wird hierbei nicht
beigemischt. Jeder Modellaufruf über V-Mind erhält einen begrenzten Ausschnitt aus
Projektstand und vorigen Nachrichten zusätzlich zum Fachwissen. Der Verlauf ist
unvalidierter Arbeitsbericht, keine Garantie für richtig ausgeführte Arbeit.

Extern arbeitende KIs müssen über die Werkzeugschnittstelle Projektereignisse und
Nachrichten melden sowie beim Start `resume` lesen. V-Mind beobachtet keine fremden
Apps automatisch. Eine vollständige automatische Codex-/ChatGPT-Anbindung ist noch
nicht eingerichtet. Die Projektanweisungen in `AGENTS.md` beschreiben den Ablauf.
Anfragen innerhalb desselben Gesprächs sollten nacheinander ausgeführt werden;
parallele Generierungen werden noch nicht pro Gespräch gesperrt.

## Verwendung durch KI-Werkzeuge

`recall` liefert vollständige Einträge samt Quelle und Nachweis, ohne ein Modell
aufzurufen. Das ist die bevorzugte Anbindung für eine bereits vorhandene KI.
`ask` ist zusätzlich ein lokaler Testclient für Ollama.

```sh
cargo run -p vmind-cli --locked -- --json --scope beispiel recall vmind.db 'SQLite Migration'
```

Für länger laufende Clients:

```sh
cargo run -p vmind-cli --locked -- serve vmind.db
```

Danach wird ein JSON-Objekt pro Eingabezeile verarbeitet. Das eigene Protokoll ist
in [docs/protocol.md](docs/protocol.md) beschrieben; es ist kein MCP-Server.
Eine automatische Anbindung an Codex/ChatGPT ist damit noch nicht eingerichtet.

## Konfiguration und Grenzen

- `VMIND_SCOPE`: Standardbereich, sonst `global`. `--scope` hat Vorrang.
- `VMIND_OLLAMA_URL`: sonst `http://127.0.0.1:11434`. Der erste Adapter unterstützt HTTP.
- `VMIND_MODEL`: sonst `vmind-gemma4:e2b`. Keine automatische Cloud-Ausweichverbindung.
- Automatischer Modellkontext: maximal drei validierte Treffer, je 600 Zeichen für
  Problem/Lösung, 300 für Quelle/Nachweis und 100 für den Prüfer. Kürzungen sind
  im Modellkontext mit `truncated` markiert; `show` liefert den vollständigen Eintrag.
  Dazu kommen höchstens acht Aufgaben, drei Entscheidungen, drei letzte Ereignisse
  und sechs letzte Chatnachrichten. Projekttexte sind auf 250 Zeichen pro Ereignis,
  Quellen auf 100 und Chatnachrichten auf 600 Zeichen begrenzt. `resume`, `journal`
  und `messages` liefern die vollständigen gespeicherten Texte.
- Maximal 2.000 Zeichen für die Frage, 8.192 Kontext-Tokens, 512 Antwort-Tokens,
  180 Sekunden Zeitlimit. Zeichenlimits sind keine exakte Tokenzählung.
- Abgeschnittene, leere, unvollständige und HTTP-Fehlerantworten werden als Fehler gemeldet.
- FTS5 sucht Wörter, keine Bedeutungen oder beliebigen Wortteile; keine automatische
  Übersetzung, Wortstammbildung, semantische Suche oder Konflikterkennung.
- Bereichstrennung steuert die Relevanz, ist keine Zugriffskontrolle. `show` und
  `get` lesen ausdrücklich angegebene IDs unabhängig vom Bereich.
- Ein lokales Programm mit Schreibzugriff auf die Datenbank kann die Daten ändern.
  Die Historie ist nachvollziehbar, aber nicht kryptografisch manipulationssicher.
- Inhalte liegen als Klartext vor. Keine Benutzerverwaltung oder Verschlüsselung.

## Entwicklung und Daten

Cargo verwendet standardmäßig `target/` im Projektordner. Für einen lokalen
SSD-Buildpfad kann eine nicht versionierte `.cargo/config.toml` angelegt werden.
Datenbanken, Gesprächsverläufe, Backups und Builddateien sind nicht Teil des Repositorys.
Der Rust-Kern wurde lokal mit Rust/Cargo 1.95.0 geprüft.

```sh
cargo test --workspace --locked
```

```sh
cargo clippy --workspace --all-targets --locked -- -D warnings
```

```sh
cargo fmt --all -- --check
```

Migration 0001 wurde neu entworfen, weil die Migration aus dem alten Chat nicht
verfügbar war. Migration 0002 ergänzt Volltextsuche, Bereiche, Rückzug und Historie.
Migration 0003 ergänzt Projekttagebuch und Gespräche.
Beim Import alter Einträge wird keine historische Prüfzeit erfunden.
Vor Migrationen einer bestehenden Datenbank vorher mit der SQLite-Backup-API sichern; keine
laufende Datenbank blind als Einzeldatei kopieren.

Architektur und Arbeitsablauf: [docs/design.md](docs/design.md).
GPU-residente Suchindizes mit ROCm/HIP sind geplant; die systemweite ROCm-Installation
wird dafür aktuell nicht verändert.

## Lizenz

MIT, siehe LICENSE.

Beiträge und Prüfungen: [CONTRIBUTING.md](CONTRIBUTING.md).
