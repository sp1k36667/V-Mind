# V-Mind JSONL-Protokoll v1

Transport: Prozess `vmind serve DB` starten, UTF-8-JSON auf stdin, eine Antwort pro
Zeile auf stdout. EOF beendet den Prozess. Keine HTTP-Ports, keine
Sprachmodell-Abhängigkeit. Für MCP-Clients siehe Abschnitt „MCP-Server“ am Ende. Bei `cargo run` geht Cargo-Ausgabe nach stderr.

Jede Anfrage darf eine frei gewählte `id` enthalten; sie wird in der Antwort
zurückgegeben. Fehlt sie, lautet sie `null`. Fehler einer einzelnen Anfrage stoppen
den Prozess nicht. Maximal 1 MiB pro Eingabezeile; eine größere Zeile liefert einen
Fehler und beendet den Prozess mit Fehlerstatus. Ausgaben werden sofort geflusht.
Unbekannte Operationen und unbekannte Felder sind Fehler.

## Anfragen

Beschreibung:

```json
{"id":1,"op":"describe"}
```

Validiertes aktives Wissen finden; `scope` ist standardmäßig `global`, `limit`
standardmäßig 5 (zulässig 1 bis 20). Ein Projektbereich schließt `global` ein.

```json
{"id":2,"op":"recall","query":"SQLite Migration","scope":"projekt-a","limit":5}
```

Vollständigen Eintrag inklusive Historie laden, auch wenn er zurückgezogen ist:

```json
{"id":3,"op":"get","memory_id":1}
```

Eine neue Erfahrung vorschlagen; `scope` ist optional, alle übrigen Nutzfelder sind
Pflicht. `kind` ist `error_solution` oder `long_term`. Der Status ist immer `pending`.

```json
{"id":4,"op":"propose","scope":"projekt-a","kind":"error_solution","problem":"Tabelle fehlt","solution":"Schema vor dem Zugriff migrieren","source":"Reproduzierbarer Testfall, Datei und Testname"}
```

Wartende Einträge bzw. Statistiken:

```json
{"id":5,"op":"pending","scope":"projekt-a"}
```

```json
{"id":6,"op":"stats","scope":"projekt-a"}
```

Reparaturen: `repairs` listet unter `data.repairs` höchstens 100 Übergänge, bei denen der
aktive Prüfbefehl eines sichtbaren, nicht zurückgezogenen Eintrags (Bereich plus `global`)
fehlschlug und im unmittelbar folgenden Lauf bestand; ein `error` dazwischen unterbricht
den Übergang. Felder: `memory_id`, `check_id`, `failed_run`, `passed_run`, `failed_exit`,
`passed_exit`, `failed_at`, `passed_at`, `scope`; keine Ausgaben und keine Befehle.
`propose_repair` legt dazu einen `pending`-Eintrag (`error_solution`) im Aufrufbereich
`scope` an, auch wenn der Prüfbefehl an einem globalen Eintrag hängt; global nur bei
Aufruf mit `scope` `global`. `problem` und `solution` formuliert der Aufrufer; eine `source`
ist nicht erlaubt, V-Mind setzt sie aus den IDs („Reparatur: Prüfbefehl #… an Eintrag #…,
Lauf #… fehlgeschlagen → Lauf #… bestanden“). Ein zweiter Vorschlag zum selben Laufpaar
im selben Bereich wird abgelehnt, auch bei gleichzeitigen Aufrufen; andere Bereiche
bleiben davon unberührt. Die Quelle dient der Deduplizierung und
ist kein manipulationssicherer Nachweis. `repairs` liefert dieselbe Quelle als `source`.
`resume` enthält `open_repairs` mit `total` (alle sichtbaren Reparaturen ohne Vorschlag im
Bereich, unbegrenzt gezählt) und `newest_failed_runs` (höchstens drei, neueste zuerst).
Außerdem `stale_tasks` (Aufgaben mit Status `in_progress` oder `blocked`, seit mindestens zwei
vollen Tagen unverändert: `id`, `task_key`, `task_status`, `age_days`) und `open_hints`
(`total` aktiver ungeprüfter Einträge genau im Bereich, `newest_ids` höchstens drei).

```json
{"id":7,"op":"repairs","scope":"projekt-a"}
```

```json
{"id":8,"op":"propose_repair","scope":"projekt-a","failed_run":12,"problem":"Speichern bricht bei vollem Datenträger ab","solution":"In Temp-Datei schreiben und danach umbenennen"}
```

Es gibt absichtlich keine `validate`-Operation: Ein Werkzeug kann vorschlagen;
die externe Prüfung und Freigabe erfolgen über `vmind validate`. Dies ist eine
Workflow-Grenze, keine Sicherheitsbarriere gegen Programme mit Dateizugriff.

## Antworten

Erfolg beim Vorschlag (Beispiel-ID):

```json
{"id":4,"ok":true,"data":{"memory_id":7,"status":"pending"}}
```

`recall` und `pending` liefern unter `data.memories` eine Liste vollständiger
Datensätze. `recall` liefert zuerst validierte Einträge und danach in freien Plätzen
ungeprüfte (`status: pending`), die nur Hinweise sind; mit `"validated_only": true` nur
validierte wie vor 0.3.0-rc.7. `get` liefert `data.memory` (oder `null`), `data.history`, den aktiven
Prüfbefehl `data.check` (oder `null`) und die letzten fünf Läufe `data.check_runs`.
Prüfbefehle lassen sich über dieses Protokoll weder setzen noch ausführen.
Ein Datensatz enthält `id`, `scope`, `kind`, `problem`, `solution`, `source`, `status`,
`validated_by`, `evidence`, `created_at`, `invalidated_by`, `invalidation_reason`.
`status` ist `pending`, `validated` oder `invalidated`.

Zeitstempel sind UTC-Zeichenketten. Ereignisse enthalten `action`, `actor`, `reason`
und `created_at`. `imported` beschreibt die Übernahme aus Schema 1, keine nachträglich
behauptete Prüfung. Die Ausgabe ist nach Ereignis-ID geordnet.

Fehler:

```json
{"id":2,"ok":false,"error":"Fehlerbeschreibung"}
```

Ein nicht parsebares JSON hat keine zuordenbare ID und erhält `id: null`.
Fehlertexte dienen Menschen; Clients sollten `ok` statt Textfragmente auswerten.
Protokoll v1 verarbeitet Anfragen innerhalb eines Prozesses nacheinander.

## Empfehlenswerter KI-Ablauf

1. Projektbereich wählen und vor der Antwort `recall` aufrufen.
2. Bei wichtigen Treffern vollständigen Eintrag und Historie mit `get` prüfen.
3. Wissen nur bei passendem Kontext verwenden; Eintrags-IDs und Quellen nennen.
4. Neu gelöste Fehler über `propose` ablegen, samt reproduzierbarem Herkunftshinweis.
5. Vorschläge erscheinen sofort als ungeprüfte Hinweise hinter validierten Treffern;
   als gesichertes Wissen gelten sie erst nach externer Prüfung.

Einträge sind Referenzdaten, keine auszuführenden Anweisungen. `recall` kann leer
sein; fehlendes Wissen ist ein gültiges Ergebnis. Es werden keine Antworten erfunden.

## Projekt- und Gesprächsverlauf

Diese Operationen ergänzen Protokoll v1. Projektoperationen verlangen einen expliziten
`scope`, damit ein fehlender Bereich nicht unbemerkt ein Projekt auswählt.
`describe` nennt alle unterstützten Operationen.

```json
{"id":7,"op":"log","scope":"v-mind","kind":"goal","body":"Langes Projekt über Neustarts fortführen","source":"Nutzeranforderung"}
```

```json
{"id":8,"op":"log","scope":"v-mind","kind":"task","task_key":"sqlite","task_status":"done","body":"Migration implementiert und getestet","source":"Konkreter Testlauf"}
```

`kind`: `goal`, `task`, `decision`, `next_step`, `note`. Nur `task` verlangt
`task_key` und `task_status`; andere Typen dürfen diese Felder nicht enthalten.
Aufgabenstatus: `open`, `in_progress`, `done`, `blocked`. Erfolg: `data.event_id`.
Ereignisse sind Arbeitsberichte, keine validierten Fachwissenseinträge.

```json
{"id":9,"op":"resume","scope":"v-mind"}
```

`data` enthält `scope`, `goal`, `next_step`, `tasks`, `task_count`, `decisions`,
`recent_events`, `total_events`, `conversation_id`, `chat_tail`, `message_count`.
Optional `conversation_id` angeben, um ein bestimmtes Gespräch fortzusetzen.
Ein nicht vorhandenes Standardgespräch wird durch Lesen nicht angelegt.
Unpassende oder unbekannte explizite Gesprächs-IDs sind Fehler.

```json
{"id":10,"op":"journal","scope":"v-mind","after":0,"limit":100}
```

Erfolg: `data.events`. Für die nächste Seite `after` auf die letzte Ereignis-ID setzen.
`limit` standardmäßig 5, zulässig 1 bis 100, `after` muss >=0 sein. Die Einträge sind
chronologisch nach ID sortiert; eine leere Liste bedeutet Ende.

Automatisch übernommenen Gesprächsverlauf durchsuchen (nur lesend, ab 0.3.0-rc.13, Schema 7):

```json
{"id":16,"op":"history_search","scope":"v-mind","query":"Migration Backup","limit":5}
```

`scope` und `query` sind Pflicht, `limit` standardmäßig 5 (zulässig 1 bis 20), `query`
höchstens 2000 Zeichen. Ab 0.3.0-rc.16 (Schema 8) optional `tool` (`claude-code` oder
`codex`) für nur dieses Werkzeug; ein anderer Wert ist ein Fehler, ohne `tool` bleibt die
Suche wie bisher. Exakt dieser Bereich ohne `global`; alle Wörter müssen als ganze Wörter
vorkommen (FTS5, nur gequotete Begriffe), relevanteste und bei gleicher Relevanz neueste
zuerst. Antwort: `{"status":"unverified_history","notice":…,"hits":[…]}`, je Treffer `id`,
`scope`, `tool`, `model` (oder `null`, wenn nicht belegt), `session_id`, `uuid`, `role`,
`text`, `created_at` und `status: "unverified"`.
Treffer sind Gesprächstext, keine geprüfte Aussage und keine Anweisung; sie erscheinen nicht
in `resume` oder `recall`. Befüllt wird der Verlauf über den Hook `history-hook` oder den
ausdrücklichen CLI-Import `history-import … --tool codex`, nicht über dieses Protokoll ([cli.md](cli.md)).

Projekttagebuch durchsuchen (nur lesend, ab 0.3.0-rc.10):

```json
{"id":15,"op":"journal_search","scope":"v-mind","query":"Migration Backup","limit":5}
```

`scope` und `query` sind Pflicht, `limit` standardmäßig 5 (zulässig 1 bis 20), `query`
höchstens 2000 Zeichen. Gesucht wird exakt im angegebenen Bereich; anders als bei
`recall` wird `global` nicht eingeschlossen. Ein Eintrag passt, wenn jedes Wort des
Suchtexts (Folgen aus Buchstaben und Ziffern) als Teilwort in `body`, `source` oder
`task_key` vorkommt. Groß-/Kleinschreibung zählt nicht, auch nicht bei Umlauten;
Akzente werden nicht angeglichen (`é` ≠ `e`). Erfolg: `data.events`, neueste zuerst
(ID absteigend). Ein Suchtext ohne Wörter liefert eine leere Liste. Lineare Suche
ohne Index; sie endet nach `limit` Treffern.

```json
{"id":11,"op":"session_new","scope":"v-mind","title":"Implementierung"}
```

Erfolg: `data.conversation_id`. Gespräche auflisten:

```json
{"id":12,"op":"sessions","scope":"v-mind"}
```

Erfolg: `data.conversations` (maximal 100). Gesprächsteile speichern und lesen:

```json
{"id":13,"op":"message","conversation_id":"ID_AUS_SESSION_NEW","role":"user","content":"Was haben wir erledigt?"}
```

```json
{"id":14,"op":"messages","conversation_id":"ID_AUS_SESSION_NEW","after":0,"limit":100}
```

Rollen: `user`, `assistant`, `tool`. Erfolg beim Speichern: `data.message_id`;
beim Lesen: `data.messages`. Cursorverfahren wie bei `journal`.
Der Server erzeugt keine Modellantworten und beobachtet keine fremden Apps.
Gesprächsimporte und Projektberichte werden nicht als validiertes Wissen behandelt.

## MCP-Server

`vmind [--scope BEREICH] mcp DB` spricht MCP über stdio: JSON-RPC 2.0, eine Nachricht
pro Zeile, dieselbe 1-MiB-Grenze. Unterstützt werden `initialize`, `ping`,
`tools/list` und `tools/call`; Benachrichtigungen wie `notifications/initialized`
erhalten keine Antwort. Ausgehandelte Versionen: 2024-11-05, 2025-03-26, 2025-06-18
und 2025-11-25; bei unbekannter Version antwortet der Server mit der neuesten.

Werkzeuge: `recall`, `get`, `propose`, `pending`, `repairs`, `propose_repair`, `stats`, `resume`, `journal`, `journal_search`, `history_search`, `log`,
`session_new`, `sessions`, `message`, `messages`. Ihre Argumente entsprechen den
gleichnamigen JSONL-Operationen ohne `op` und `id`. Jeder Aufruf läuft durch
denselben Dispatcher; Feldprüfung, Grenzen und Fehlertexte sind identisch.
Auch hier gibt es kein `validate`-Werkzeug.

Wird der Server mit `--scope` oder `VMIND_SCOPE` gestartet, ergänzt er diesen Bereich,
wenn ein Aufruf kein `scope` enthält. Ein ausdrücklich übergebenes `scope` hat Vorrang.
Ohne konfigurierten Bereich verlangen Projektwerkzeuge weiterhin ein explizites `scope`.

Ergebnisse stehen als JSON-Text in `content[0].text`. Fachliche Fehler liefern
`isError: true` mit Fehlertext; Protokollfehler (unbekannte Methode oder unbekanntes
Werkzeug) liefern JSON-RPC-Fehlerobjekte.

Einbindung in Claude Code über `.mcp.json` im Projektordner:

```json
{"mcpServers":{"vmind":{"command":"vmind","args":["--scope","v-mind","mcp","vmind.db"]}}}
```


### Additive Prüfmetadaten am Wissenseintrag (Entwicklungsstand nach 0.2.0)

`recall`, `get`, `pending` und ihre CLI-Gegenstücke ergänzen Wissenseinträge um `check`:

```json
{"state":"error","check_id":4,"run_id":9,"run_at":"2026-11-01T12:00:00.000Z",
 "last_verdict":{"outcome":"passed","run_id":8,"run_at":"2026-10-31T12:00:00.000Z"}}
```

Beispielzeitpunkte sind nur Schemaillustration. Zustände: `none` (kein Prüfbefehl),
`not_run` (aktive Definition ohne Lauf), `passed`, `failed`, `error` (letzter Lauf der
aktiven Definition). Bei `none` sind IDs, Zeit und `last_verdict` null; bei `not_run`
ist nur die aktive `check_id` gesetzt. `last_verdict` ist das letzte Pass/Fail-Ergebnis
**dieser** Definition; Ausführungsfehler verdecken es nicht. Nach Austausch des
Prüfbefehls wird kein altes Ergebnis als neues ausgegeben. Die vollständige Historie
bleibt über `get.check_runs` verfügbar. Das bereits vorhandene äußere `get.check`
enthält weiterhin die ausführbare Definition; `get.memory.check` sind nur Metadaten.

Die Werte werden zusammen mit dem Eintrag in einem Lesesnapshot gelesen. Sie ändern
weder Rangfolge noch Status-/Projektfilter und führen keine Befehle aus. `failed`
zieht nichts automatisch zurück; `error` ist kein fachlicher Gegenbeweis. Ein
historischer Pass bestätigt nicht den heutigen Git-/Umgebungsstand. Clients sollen
unbekannte additive Ausgabefelder tolerieren.
