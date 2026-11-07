# V-Mind ausführlich: Kommandozeile, Projektgedächtnis und Grenzen

Diese Seite ergänzt die [README](../README.de.md). Sie beschreibt alle Befehle,
den Ablauf für lange Projekte, Konfiguration, Grenzen und Entwicklungshinweise.

## Betrieb und Produktreife

Im Entwicklungsstand nach 0.2.0: `vmind doctor DB` prüft die Datenbank rein lesend;
`vmind backup DB ZIEL` erstellt eine geprüfte Sicherung ohne vorhandene Dateien zu
überschreiben. Vor einem Schemawechsel wird automatisch gesichert. Details und
Wiederherstellung: [Betrieb](operations.md). Offene Abnahmekriterien:
[Produktreife](product-readiness.md).

### Journalmodus (Entwicklungsstand)

Neue Datenbanken behalten den SQLite-Standard (`delete`); V-Mind stellt nie von selbst um.
`vmind doctor DB` zeigt den aktuellen Modus. Ausdrücklich umstellen:

```sh
vmind journal-mode vmind.db wal
```

Vorher entsteht eine geprüfte Sicherung neben der Datenbank (oder in `VMIND_BACKUP_DIR`).
Mit `wal` legt SQLite neben der Datei die Zusatzdateien `vmind.db-wal` und `vmind.db-shm` an;
sie gehören zur Datenbank, haben dieselben Rechte und dürfen nicht einzeln kopiert oder
gelöscht werden. Zum Sichern immer `vmind backup` verwenden. Liest oder schreibt ein anderer
Prozess gerade (offene Transaktion, etwa MCP-Server oder `vmind serve` mitten in einer
Anfrage), schlägt der Wechsel mit dieser Meldung fehl und der Modus bleibt; offene, aber
untätige Verbindungen blockieren nicht in jedem Fall. Andere Fehler (zum Beispiel
schreibgeschützte Datei oder voller Datenträger) werden mit ihrer Ursache gemeldet. In beiden
Fällen bleibt die vorher angelegte Sicherung erhalten.
Zurück mit `vmind journal-mode vmind.db delete`; danach verschwinden die Zusatzdateien, sobald
die letzte Verbindung geschlossen ist.

Lesender Zugriff (`doctor`, `backup`, `report`) auf eine WAL-Datenbank ohne vorhandene
Zusatzdateien kann die `-shm`-Datei neu anlegen und dafür Schreibrecht im Ordner der
Datenbank brauchen, auch wenn die Datenbank selbst nur gelesen wird.

Gemessen mit zwei gleichzeitig schreibenden Prozessen (je 12.000 Schreibvorgänge, isolierte
Testdatenbank auf ext4-SSD): mit `wal` etwa 8–9 s statt 32–34 s, ohne Sperrfehler. `wal`
braucht ein lokales Dateisystem mit gemeinsamem Speicher; auf Netzlaufwerken nicht verwenden.
Auf einem lokalen NTFS-Laufwerk (Linux-Treiber `ntfs3`) funktionierten Wechsel, `doctor`,
Sicherung und Rückwechsel, gleichzeitiger Betrieb aber nicht zuverlässig: Starten zwei
Prozesse gleichzeitig, solange noch keine `-shm`-Datei existiert, bricht einer davon oft mit
„disk I/O error“ ab (SQLite `SQLITE_IOERR_SHMMAP`). Gegenprobe mit je zwei gleichzeitig
startenden Prozessen und einem Schreibvorgang, 100 Wiederholungen: ntfs3 70 von 200
Öffnungen fehlgeschlagen, ext4 0 von 200. Der betroffene Prozess meldet den Fehler und endet;
es geht nichts still verloren. Unter Linux mit `ntfs3` und auf Netzlaufwerken daher beim
Standard `delete` bleiben, der keine `-shm`-Datei nutzt. Gemessen wurde nur der Linux-Treiber
`ntfs3`, nicht NTFS unter Windows.

### Geheimnis-Audit (Entwicklungsstand)

`vmind audit-secrets DB` durchsucht eine vorhandene Datenbank rein lesend in einem
Snapshot nach bekannten Geheimnisformaten. Es legt nichts an, stellt kein Schema um
(ältere Schemas werden mit ihren Tabellen geprüft) und gilt für alle Bereiche;
`--scope` wird nicht beachtet. Durchsucht werden alle Zeilen dieser Felder:

| Tabelle | Felder |
| --- | --- |
| `memories` | scope, problem, solution, source, validated_by, evidence |
| `memory_events` | actor, reason (Kopien von Quelle und Nachweis) |
| `invalidations` | actor, reason |
| `project_journal` | scope, task_key, body, source |
| `conversations` | id, scope, title |
| `chat_messages` | content, bei JSON zusätzlich jede dekodierte Zeichenkette |
| `memory_checks` | argv (auch dekodiert), workdir, set_by |
| `check_runs` | output |
| `observations` | scope, session_id, tool_use_id, paths (auch dekodiert) |

Erkannte Formate (Heuristik, Wortgrenze davor): privater Schlüsselblock, GitHub-Token
(`ghp_` usw., `github_pat_`), `sk-`-Schlüssel, Stripe-Live-Schlüssel, AWS-Zugangsschlüssel
(`AKIA`/`ASIA`), Slack-Token, Google-API-Schlüssel. **Unsicher**, weil Beispiele genauso
aussehen: JWT und `schema://NUTZER:PASSWORT@` (Platzhalter wie `***`, `<…>`, `{…}`,
`$VAR` zählen nicht). Allgemeine Wörter wie „token“ oder „password“, Hashes, UUIDs und
Base64 werden bewusst nicht gemeldet.

Ausgabe je Fund: Tabelle, Zeilennummer, Feld, Fundart, ob unsicher, sowie der betroffene
Wissenseintrag (`memory_id`) oder die rowid des Gesprächs. Nie Feldwerte, Textausschnitte
oder Text-IDs; bei `conversations` steht deshalb die rowid. Funde sind kein Fehler
(Exit 0); einen Fehler gibt es nur, wenn nicht durchsucht werden konnte (Datei fehlt,
keine V-Mind-Datenbank, unbekanntes neueres Schema).

Grenzen: Kein Fund heißt nicht geheimnisfrei. Prüfausgaben sind nur gekürzt gespeichert
(letzte 4000 Zeichen); dort angeschnittene Geheimnisse werden nicht erkannt. Andere
Kodierungen als JSON (Base64, URL-Kodierung) werden nicht dekodiert. Nicht durchsucht:
Suchindizes (`memories_fts*`, `memories_trigram*`), freie Seiten und `-journal`/`-wal`
der Datei, Sicherungen und andere Kopien. Das Audit löscht nichts.

## Startprompt für die nutzende KI

Die vollständige gemeinsame Startanweisung liegt in `prompts/start.de.md`.
Der Ollama-Adapter verwendet genau diese Datei als Systemprompt. Änderungen daran
werden beim nächsten Build bzw. erneuten Installieren übernommen.

```sh
vmind start-prompt
```

Englische, inhaltsgleiche Fassung (`prompts/start.en.md`):

```sh
vmind start-prompt en
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

`repairs DB` listet nur lesend Prüfbefehle, die fehlschlugen und im direkt folgenden
Lauf bestanden (Bereich plus `global`, ohne zurückgezogene Einträge und ersetzte
Prüfbefehle). `propose-repair DB LAUF PROBLEM LÖSUNG` legt dazu je Bereich genau einen
ungeprüften Vorschlag im gewählten `--scope` an, auch bei einem globalen Prüfbefehl; LAUF ist `failed_run` aus `repairs`, die Quelle erzeugt V-Mind aus den IDs.
Ausgaben und Befehle der Läufe werden nicht übernommen, und nichts wird validiert.
Grenze: V-Mind sieht nur Prüfbefehle an eigenen Einträgen, nicht die übrigen Tests eines
Projekts.

`resume` (CLI, JSONL, MCP) und `report` nennen unter `open_repairs` die echte Zahl der
Reparaturen ohne Vorschlag im gewählten Bereich (`total`, gleiche Sichtbarkeit wie
`repairs`, nicht auf 100 begrenzt) und höchstens drei neueste `failed_run`-IDs
(`newest_failed_runs`). Die Textausgabe zeigt dann eine Zeile mit dem Hinweis auf
`propose-repair`; ohne offene Reparatur entfällt sie. Es werden keine Texte, Befehle oder
Ausgaben gezeigt und nichts geschrieben.

Besteht `check DB ID` oder ein Lauf in `revalidate` direkt nach einem Fehlschlag desselben
aktiven Prüfbefehls, nennt die Ausgabe genau diese Reparatur: im Text eine Zeile
„Reparatur erkannt … propose-repair DB LAUF PROBLEM LÖSUNG“, in JSON `repair` (bei `check`,
sonst `null`) bzw. `repairs` (bei `revalidate`). Es gelten der gewählte `--scope`, die
Sichtbarkeit von `repairs` und die Deduplizierung: Gibt es im Bereich schon einen
Vorschlag, entfällt der Hinweis. Der Hinweis schreibt nichts; scheitert seine Abfrage,
bleibt der Lauf gespeichert und das Ergebnis unverändert.

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

### Fehlerhinweise für Claude Code (`hint`, ab 0.3.0-rc.8)

Schlägt ein Werkzeugaufruf fehl, kann ein `PostToolUseFailure`-Hook passendes Wissen direkt
in den Kontext der KI geben, ohne dass sie selbst an `recall` denken muss:

```json
{
  "hooks": {
    "PostToolUseFailure": [
      {"matcher": "Bash", "hooks": [{"type": "command",
        "command": "vmind --scope v-mind hint \"$CLAUDE_PROJECT_DIR/vmind.db\""}]}
    ]
  }
}
```

`hint` sucht mit den ersten 1000 Zeichen des Hook-Feldes `error` (wie `recall`, mit
ungeprüften Hinweisen, höchstens 3 Treffer) und gibt die Treffer als `additionalContext`
zurück, markiert als `[geprüft]` oder `[UNGEPRÜFT]`, Problem, Lösung und Quelle je auf 300
Zeichen gekürzt. Die Analyse macht weiter die KI; V-Mind liefert nur, was schon einmal gelöst
wurde. **Nur lesend:** Fehlertext, Befehl und Ausgabe werden weder gespeichert noch im Kontext
wiederholt, nichts wird ausgeführt. Ohne Treffer, bei anderen Ereignissen, ungültiger
Eingabe, fehlender oder älterer Datenbank und wenn die Datenbank länger als 0,5 s gesperrt ist,
gibt der Hook nichts aus und endet erfolgreich; er blockiert nie ein Werkzeug und legt keine
Datenbank an. In einer echten Claude-Code-Sitzung ist er noch nicht erprobt.

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

Ohne Angabe liefert `recall` höchstens 5 Treffer. Mit `--limit N` (1 bis 20, wie
`limit` in JSONL und MCP) mehr oder weniger, zum Beispiel wenn eine Aufgabe zu vielen
gespeicherten Erfahrungen passt:

```sh
cargo run -p vmind-cli --locked -- --json --scope beispiel recall vmind.db 'SQLite Migration' --limit 10
```

Ab 0.3.0-rc.7 füllen ungeprüfte aktive Einträge (`pending`) die Plätze, die nach allen
validierten Suchstufen frei bleiben, mit denselben Suchstufen. Validierte Treffer und ihre
Reihenfolge bleiben unverändert vorn; Bereichs- und Rückzugsfilter gelten wie bisher. In der
Textausgabe steht vor jedem ungeprüften Treffer „UNGEPRÜFT – nur Hinweis“, in JSON zeigt
`status` den Zustand, im Ollama-Kontext stehen sie getrennt unter `unconfirmed_hints`.
`--validated-only` (JSONL/MCP `validated_only: true`) liefert genau das bisherige Verhalten.
Validiert wird dadurch nichts; dafür bleiben `validate` und Prüfbefehle zuständig.

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
  Zeichen je Begriff) auf, etwa „Filter“ in „Testfilter“. Das gilt nur in dieser Richtung:
  Eine längere gebeugte Form in der Frage („Rundungsfehlern“) findet die kürzere gespeicherte
  („Rundungsfehler“) nicht ([Abrufkorpus](experiments/abruf-korpus.md)). Keine Bedeutungen,
  keine automatische Übersetzung, keine semantische Suche oder Konflikterkennung.
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
