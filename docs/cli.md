# V-Mind ausführlich: Kommandozeile, Projektgedächtnis und Grenzen

Diese Seite ergänzt die [README](../README.de.md). Sie beschreibt alle Befehle,
den Ablauf für lange Projekte, Konfiguration, Grenzen und Entwicklungshinweise.

## Betrieb und Produktreife

Im Entwicklungsstand nach 0.2.0: `vmind doctor DB` prüft die Datenbank rein lesend;
`vmind backup DB ZIEL` erstellt eine geprüfte Sicherung ohne vorhandene Dateien zu
überschreiben. Vor einem Schemawechsel wird automatisch gesichert. Details und
Wiederherstellung: [Betrieb](operations.md). Offene Abnahmekriterien:
[Produktreife](product-readiness.md).

## Startprompt für die nutzende KI

Die vollständige gemeinsame Startanweisung liegt in `prompts/start.de.md`.
Der Ollama-Adapter verwendet genau diese Datei als Systemprompt. Änderungen daran
werden beim nächsten Build bzw. erneuten Installieren übernommen.

```sh
vmind start-prompt
```

Für externe KI-Clients die Anweisung als Startkonfiguration übernehmen und zusätzlich
die realen Werkzeuge, Datenbank, Projektbereich und Gesprächs-ID anbinden. Der Prompt
richtet keine Verbindung ein. Details: [docs/start-prompt.md](start-prompt.md).

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

## Prüfbefehle

Ein Prüfbefehl verbindet einen Eintrag mit einem ausführbaren Test. Setzen:

```sh
vmind check-set vmind.db 1 'Name' /pfad/zum/projekt cargo test -p meinpaket --test api -- --exact neuer_fall
```

Aufbau: `check-set DB ID AKTEUR ORDNER BEFEHL [ARG...]`. Der Ordner muss existieren und
wird als absoluter Pfad gespeichert. Alle Wörter nach dem Ordner bilden den Befehl;
sie werden ohne Shell übergeben, also ohne Platzhalter, Umleitungen oder Verkettungen.
Wer eine Shell braucht, muss sie ausdrücklich aufrufen (`sh -c '...'`); dann steht
genau das im Eintrag und ist sichtbar. Ein erneutes `check-set` ersetzt den aktiven
Prüfbefehl; frühere bleiben mit ihren Läufen in der Datenbank.

Ausführen:

```sh
vmind check vmind.db 1
```

```sh
vmind --scope projekt revalidate vmind.db
```

Ergebnisse und Folgen:

| Ergebnis | ungeprüfter Eintrag | validierter Eintrag |
|---|---|---|
| bestanden (Exit 0) | wird validiert, Prüfer `vmind check` | bleibt validiert |
| fehlgeschlagen (Exit ≠ 0) | bleibt ungeprüft | wird gemeldet; mit `--invalidate` zurückgezogen |
| Fehler (nicht startbar, Zeitlimit) | keine Änderung | keine Änderung |

Jeder Lauf wird mit Ergebnis, Exit-Code, Dauer und den letzten 4.000 Zeichen der
Ausgabe gespeichert; `show DB ID` zeigt Prüfbefehl und die letzten fünf Läufe.
`check` und `revalidate` enden mit Fehlerstatus, wenn etwas nicht bestanden hat, und
eignen sich damit für Skripte und CI. `revalidate` prüft alle nicht zurückgezogenen
Einträge mit Prüfbefehl im gewählten Bereich plus `global`, höchstens 1.000.
Zeitlimit pro Befehl: `VMIND_CHECK_TIMEOUT` in Sekunden (1 bis 3.600, sonst 300).

Grenzen und Sicherheit:

- Ein bestandener Befehl beweist nur, was er prüft. `cargo test` mit einem
  vertippten Filter führt null Tests aus und endet trotzdem mit Exit 0. Mit
  `--exact` und vollständigem Namen arbeiten und die gespeicherte Ausgabe ansehen
  („1 passed“). `pytest` endet bei null gefundenen Tests dagegen mit Fehler.
- Prüfbefehle lassen sich nur über die Kommandozeile setzen und ausführen. JSONL
  und MCP zeigen sie über `get` an, können sie aber weder setzen noch starten.
- Befehle laufen mit den Rechten und Umgebungsvariablen des aufrufenden Nutzers.
  Vor `check-set` den Befehl lesen wie jeden anderen Befehl, den man ausführt.
- Wer Schreibzugriff auf die Datenbankdatei hat, kann Prüfbefehle direkt ändern.
  `revalidate` nur auf eigenen, vertrauenswürdigen Datenbanken ausführen.

### Prüfergebnis direkt beim Abruf (Entwicklungsstand nach 0.2.0)

`recall`, `show`, `pending`, `report` und der Ollama-Kontext enthalten `check` pro
Wissenseintrag. Es beschreibt ausschließlich die **aktive** Prüfbefehlsdefinition:
`none` = kein Prüfbefehl (manuelle Nachweise bleiben möglich), `not_run` = noch kein
Lauf, sonst `passed`, `failed` oder `error` für den letzten Lauf. IDs und Zeitpunkte
machen den Befund nachlesbar. Ein Ausführungsfehler verdeckt den letzten Pass/Fail-
Befund dieser Definition nicht (`last_verdict`).

Ein Fehlschlag wird sichtbar gewarnt, ändert den gespeicherten Status aber nur bei
bewusstem Rückzug. Die Abrufrangfolge und Status-/Bereichsfilter bleiben unverändert.
Eine ersetzte Definition übernimmt kein früheres Testergebnis: Sie beginnt mit
`not_run`. Der Abruf führt nichts aus; auch ein `passed` bestätigt nicht den heutigen
Git-Commit, die aktuelle Umgebung oder die fachliche Erklärung des Eintrags.

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

Die Übersicht enthält das aktuelle Ziel, den nächsten Schritt, den aktuellen Stand aller
unerledigten Aufgaben (höchstens 20) und der fünf zuletzt erledigten, fünf Entscheidungen,
fünf letzte ergänzende Ereignisse wie Notizen, die nicht schon darüber stehen, und zehn letzte
Chatnachrichten. Texte werden nicht gekürzt. Gesamtzahlen zeigen, ob weitere Daten
vorhanden sind.
Die vollständige Historie bleibt seitenweise verfügbar, jeweils maximal 100 Einträge:

```sh
vmind --scope v-mind journal vmind.db
```

Für die nächste Seite die letzte ausgegebene Ereignis-ID als weiteres Argument
angeben. Dasselbe Cursorverfahren gilt für `messages DB GESPRÄCH_ID [NACH_ID]`.
Eine Übersicht allein enthält also nicht jede Zeile eines monatelangen Projekts.

Im Entwicklungsstand nach 0.2.0 enthält `resume.recent_events` keine überholten
Ziel-, Aufgaben- oder nächste-Schritt-Meldungen mehr. Der aktuelle Zustand steht in
den dafür vorgesehenen Feldern; vollständige frühere Versionen bleiben in `journal`.
Dies verhindert widersprüchliche Zustandsdarstellungen, garantiert aber keine richtige
Interpretation durch ein Modell.

Für Menschen gibt es einen lesbaren Bericht in Markdown:

```sh
vmind --scope v-mind report vmind.db > projektbericht.md
```

Er zeigt Ziel, nächsten Schritt, Aufgaben (blockierte und laufende zuerst), die letzten
Entscheidungen, bis zu 20 geprüfte Einträge mit Bestätigung und letztem Prüflauf sowie
ungeprüfte Vorschläge getrennt davon. Er öffnet ausschließlich eine vorhandene Datenbank mit aktuellem Schema rein lesend
und liest alle Abschnitte aus einem gemeinsamen SQLite-Snapshot. Bei einem älteren
Schema fordert er ein bewusstes Upgrade, statt zu migrieren. Er enthält nichts, was nicht
gespeichert ist; Lücken stehen ausdrücklich als „noch nicht gespeichert“ da. Mit `--json`
kommen dieselben Daten als JSON.

### Beobachtungen aus Claude Code (ab Schema 6)

Damit ein Projektstand nicht davon abhängt, dass die KI ans Mitschreiben denkt, kann
Claude Code jeden Bash-, Edit- und Write-Aufruf über einen Hook an V-Mind melden. In
`.claude/settings.local.json` des Projekts:

```json
{
  "hooks": {
    "PostToolUse": [
      {"matcher": "Bash|Edit|Write", "hooks": [{"type": "command",
        "command": "vmind --scope v-mind observe \"$CLAUDE_PROJECT_DIR/vmind.db\""}]}
    ],
    "PostToolUseFailure": [
      {"matcher": "Bash|Edit|Write", "hooks": [{"type": "command",
        "command": "vmind --scope v-mind observe \"$CLAUDE_PROJECT_DIR/vmind.db\""}]}
    ]
  }
}
```

`observe` liest die Hook-Meldung von stdin und speichert in einer eigenen Tabelle nur
Sitzungs-ID, Aufruf-ID, Werkzeug, Ergebnis (`completed` oder `failed`) und bei Edit/Write
den Dateipfad relativ zum Projektordner. **Befehle, Ausgaben, Fehlertexte und
Dateiinhalte werden weder gespeichert noch ausgeführt;** Pfade außerhalb des Projekts
werden weggelassen. Dieselbe Meldung zweimal ergibt keinen zweiten Eintrag; dieselbe
Aufruf-ID mit anderem Inhalt wird abgelehnt. Andere Werkzeuge werden still ignoriert.
Projektordner und Dateipfad müssen absolut sein; `..` wird nicht als Projektpfad
übernommen. Pro Ereignis sind höchstens 20 verschiedene relative Pfade zulässig,
jeweils bis zu 400 Zeichen. Größere Meldungen werden abgelehnt, nicht still gekürzt.
Dateipfade und Sitzungskennungen sind selbst Metadaten, die vertraulich sein können.
Hooks bewusst aktivieren; gelesene Zusammenfassungen können über den Modell-Host
weitergegeben werden.
`observe` legt keine Datenbank an und stellt kein Schema um: Ist die Datenbank älter,
meldet der Hook einen Fehler, bis das Upgrade bewusst ausgeführt wurde.

`resume` und `report` zeigen die letzten drei Sitzungen zusammengefasst (Zeitraum,
Anzahl Aufrufe und Fehlschläge, Anzahl Dateien, bis zu fünf zuletzt betroffene Pfade)
und die Gesamtzahl; der Ollama-Adapter übergibt ebenfalls eine begrenzte Zusammenfassung
als nicht geprüfte Hostbeobachtung. Pfade im Modellkontext können gekürzt sein.
Beobachtungen stehen nicht im Projekttagebuch und verdrängen dort
nichts. **Beobachtet heißt nicht geprüft:** Ein abgeschlossener Bash-Aufruf ist kein
bestandener Test, keine erledigte Aufgabe und keine Validierung. Unterstützt ist nur
Claude Code; für den Chat der Desktop-App oder andere Clients gibt es keine Hooks.
Beobachtungen werden derzeit nie automatisch gelöscht; die Tabelle wächst mit jeder
Sitzung. Ein geprüfter Befehl zum Aufräumen folgt später.

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
in [docs/protocol.md](protocol.md) beschrieben.

MCP-fähige Clients starten stattdessen den MCP-Server. Mit `--scope` wird der
Standardbereich gesetzt; Validierung bleibt auch hier der CLI vorbehalten:

```sh
vmind --scope v-mind mcp vmind.db
```

Für Claude Code liegt im Projektordner eine `.mcp.json`, die genau diesen Aufruf
einträgt. Claude Code fragt beim ersten Start nach der Freigabe des Servers.
Optional lädt ein SessionStart-Hook in `.claude/settings.local.json` (nicht im
Repository) den Projektstand automatisch zu Sitzungsbeginn:

```json
{"hooks":{"SessionStart":[{"hooks":[{"type":"command",
  "command":"vmind --scope v-mind resume \"$CLAUDE_PROJECT_DIR/vmind.db\""}]}]}}
```

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
- FTS5 sucht zuerst ganze Wörter (BM25), danach füllt eine Teilwortsuche (Trigramme, ab drei
  Zeichen je Begriff) auf, etwa „Filter“ in „Testfilter“. Dafür wird von jedem Suchwort
  höchstens eine häufige deutsche Endung abgetrennt, sodass „Rundungsfehlern“ auch
  „Rundungsfehler“ findet. Umlaut-Plurale („Passwörter“) und unregelmäßige Formen
  („Indizes“) werden nicht erkannt. Funktionswörter wie „nicht“, „vor“ oder „not“ zählen
  nicht als Suchwort. Ein Treffer muss mindestens halb so viele Suchwörter enthalten wie
  der beste ([Abrufkorpus v2](experiments/abruf-korpus-v2.md)). Keine Bedeutungen, keine
  automatische Übersetzung, keine semantische Suche oder Konflikterkennung.
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
Migration 0003 ergänzt Projekttagebuch und Gespräche. Migration 0004 ergänzt
Prüfbefehle (`memory_checks`) und Prüfläufe (`check_runs`). Migration 0005 ergänzt die
Teilwortsuche (`memories_trigram`) und baut sie für vorhandene Einträge auf. Migration
0006 ergänzt die Tabelle `observations` für Hook-Beobachtungen; bestehende Daten bleiben
unverändert.
Beim Import alter Einträge wird keine historische Prüfzeit erfunden.
Vor Migrationen einer bestehenden Datenbank vorher mit der SQLite-Backup-API sichern; keine
laufende Datenbank blind als Einzeldatei kopieren.

Architektur und Arbeitsablauf: [docs/design.md](design.md).
GPU-residente Suchindizes mit ROCm/HIP sind geplant; die systemweite ROCm-Installation
wird dafür aktuell nicht verändert.
