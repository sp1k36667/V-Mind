# Entwurf: gezieltes Entfernen von Geheimnissen (`purge`)

Status: **Entwurf zur gemeinsamen Prüfung, nicht umgesetzt.** Grundlage sind die
Abstimmungen im Teamkanal (#116, #120, #121, #131, Revision nach #134–#136) und das
lesende Audit `vmind audit-secrets` (PR #29). Dieses Dokument legt fest, was ein
späterer Befehl tun darf und wie das geprüft wird. Es verspricht keine physische
Löschung. Punkte unter [Blocker](#blocker-vor-einer-umsetzung) sind noch nicht
entschieden; vorher wird nichts umgesetzt.

## Ziel und Nicht-Ziele

**Ziel:** Ein versehentlich gespeichertes Geheimnis aus genau benannten Zeilen einer
V-Mind-Datenbank so entfernen, dass es (1) über keine V-Mind-Operation mehr lesbar ist,
(2) in keinem Suchindex mehr gefunden wird und (3) nach Abschluss nicht mehr in den
Bytes der Datenbankdatei steht.

**Nicht-Ziele:**

- Keine automatische Suche-und-Löschen-Funktion. Ziele werden einzeln mit numerischer
  ID genannt; das Audit liefert nur Hinweise.
- Keine Garantie für Datenträger (SSD-Ausgleich, Dateisystem-Snapshots, Papierkorb),
  Sicherungen, fremde Kopien, Modell-Protokolle von Claude, Codex oder anderen Hosts.
  Ein gespeichertes Geheimnis gilt immer als offengelegt und muss **widerrufen bzw.
  ersetzt** werden. Purge ist Schadensbegrenzung, kein Ersatz dafür.
- Kein MCP- oder JSONL-Werkzeug. Nur ausdrücklicher CLI-Aufruf durch einen Menschen.
- Keine Änderung an Bereichsnamen (`scope`) und Text-IDs von Gesprächen in Version 1.
- Version 1 unterstützt nur Datenbanken im Journalmodus `delete` (V-Mind-Standard),
  nicht `wal`.

## Ziele (Namensräume)

Jedes Ziel ist `NAMENSRAUM:ID` mit numerischer ID, so wie `audit-secrets` sie meldet.
Unbekannte Namensräume, nicht vorhandene IDs, Dubletten oder nichtnumerische IDs führen
zum Abbruch **vor** jeder Änderung.

| Ziel | Tabelle (Schlüssel) | Was entfernt wird |
| --- | --- | --- |
| `memory:N` | `memories.id` | problem, solution, source, validated_by, evidence des Eintrags; dazu alle Zeilen in `memory_events` (actor, reason) und `invalidations` (actor, reason) dieses Eintrags; alle `memory_checks` und deren `check_runs` des Eintrags werden gelöscht |
| `journal:N` | `project_journal.id` | body, source; nie `task_key` |
| `task:N` | alle `project_journal`-Zeilen mit Bereich und `task_key` der Zeile N | `task_key` einheitlich, siehe [Aufgabenschlüssel](#aufgabenschlüssel) |
| `conversation:R` | `conversations.rowid` | title; die Text-ID bleibt (siehe [Bezug auf Gespräche](#stabiler-bezug-auf-gespräche)) |
| `message:N` | `chat_messages.id` | content |
| `check_run:N` | `check_runs.id` | output |
| `check:N` | `memory_checks.id` | Zeile und ihre `check_runs` werden gelöscht |
| `observation:N` | `observations.id` | Zeile wird gelöscht |

**Redaktion statt Löschen**, wo Zeilen referenziert werden (`memories`, Journal,
Gespräche, Nachrichten): Die Felder erhalten einen festen Text
`[entfernt: purge #P]` (P = Nummer im Purge-Protokoll). So bleiben Fremdschlüssel,
Nachrichtenreihenfolge und Journal-Nummern gültig. Ganz gelöscht werden nur Zeilen, auf
die nichts verweist (Prüfbefehle, Prüfläufe, Beobachtungen).

**Folgen für Wissenseinträge:** Ein redigierter Eintrag darf nicht als geprüftes Wissen
weiterleben. Ist er nicht zurückgezogen, wird er im selben Vorgang zurückgezogen
(Akteur `purge`, Grund `[entfernt: purge #P]`). Seine Prüfbefehle werden gelöscht,
damit `check`/`revalidate` nie einen redigierten Befehl ausführen (`check` lehnt
zurückgezogene Einträge ohnehin ab).

### Aufgabenschlüssel

`resume` bestimmt den aktuellen Stand einer Aufgabe über die jüngste Journalzeile mit
demselben Bereich und `task_key` (`max(id)`). Würde nur in einer Zeile der Schlüssel
ersetzt, könnte ein älterer Stand derselben Aufgabe wieder als aktuell erscheinen.
Teilredaktion des Schlüssels einzelner Zeilen ist deshalb **ausgeschlossen**.

**Entschieden (#138):** Ein eigenes Ziel `task:N` (N = eine Journal-ID der Aufgabe)
ersetzt den Schlüssel in **allen** Journalzeilen desselben Bereichs und Schlüssels
einheitlich durch `purged-P`. Die Vorschau listet vorher alle betroffenen IDs. Die
Aufgabe bleibt zusammenhängend; ihr jüngster Stand bleibt der jüngste. `journal:N`
allein verändert `task_key` nie, nur `body` und `source`.

### Stabiler Bezug auf Gespräche

Alle Zieltabellen außer `conversations` haben einen `INTEGER PRIMARY KEY`; diese IDs
ändert `VACUUM` nicht. `conversations` hat eine Text-ID und eine implizite rowid, die
`VACUUM` laut SQLite-Dokumentation neu vergeben darf
([lang_vacuum](https://sqlite.org/lang_vacuum.html)). Deshalb:

- Eine rowid gilt nur innerhalb eines Plans. Der Plan wird bei jedem Commit ungültig
  (siehe Plan), also auch durch `VACUUM`; ein späterer Purge braucht eine neue Vorschau
  mit neuer Audit-Ausgabe.
- Der Plan löst die rowid intern zur Text-ID auf und hält sie nur in der Plan-Datei;
  ausgegeben wird sie nie.
- Das Purge-Protokoll speichert keine Zielidentitäten (siehe Protokoll), daher kann es
  durch neu vergebene rowids nicht falsch werden.

## Ablauf

### 1. Vorschau (rein lesend gegenüber der Datenbank)

```text
vmind purge DB --preview ZIEL [ZIEL ...]
```

- Öffnet die Datenbank wie `audit-secrets` nur lesend in einem Snapshot; legt keine
  Datenbank an, migriert nicht.
- Verlangt das aktuelle Schema und `journal_mode=delete`; sonst Abbruch mit Hinweis
  (`doctor`, `backup`, Upgrade bzw. Vorbereitung bei WAL, siehe unten).
- Ausgabe nur mit festen Bezeichnern und Zahlen: je Ziel betroffene Tabellen, Feldnamen
  und Zeilenzahlen, die Folgen (Rückzug, gelöschte Prüfbefehle, Aufgabenschlüssel),
  vermutete Kopien (Namensraum und numerische ID), **Anzahl** bekannter Sicherungen je
  Herkunft und eine zufällige **Plan-ID**. Nie Feldwerte, Ausschnitte, Text-IDs oder
  Dateipfade von Sicherungen.

**Plan statt Inhaltsprüfsumme.** Eine Prüfsumme über den Inhalt, auch eine mit
Schlüssel, wäre bei kurzen Geheimnissen ein Offline-Rateorakel. Deshalb enthält die
Bestätigung keinen Inhaltsbezug:

- Die Vorschau legt eine Plan-Datei mit Rechten 0600 an (Ort: neben der Datenbank,
  Name aus Plan-ID). Inhalt: Plan-ID, Ziele, intern aufgelöste Schlüssel (bei
  Gesprächen die Text-ID), Erstellungszeit und der **Dateiänderungszähler** von SQLite
  (Header-Bytes 24–27; wird im Journalmodus `delete` bei jedem Commit erhöht). Keine
  Feldwerte, keine Hashes über Feldwerte.
- Die Ausführung liest den Zähler unter der Exklusivsperre erneut. Weicht er ab:
  Abbruch ohne Änderung, neue Vorschau nötig.
- Der Plan wird zusätzlich an die Identität der Datenbank gebunden (z. B. Gerät,
  Inode, Dateigröße, Schemaversion; konkrete Auswahl offen), damit ein Austausch oder
  Rückspielen der Datei nicht unbemerkt bleibt.
- **Noch nicht belegt (Blocker B6):** Dass der Zähler jede Änderung zuverlässig anzeigt,
  ist eine Annahme. Vor einer Umsetzung separat zu prüfen: Austausch/Rückspielen einer
  Datei mit gleichem Zählerstand, Überlauf des 32-Bit-Zählers, Verhalten bei mehreren
  Commits unter `locking_mode=EXCLUSIVE`. Bis dahin ist der Zähler kein bewiesener
  Ersatz für eine Inhaltsprüfung.
- Die Plan-Datei wird nach erfolgreichem Commit (Schritt C) gelöscht; ein abgelaufener
  oder fremder Plan wird abgewiesen.

### 2. Ausführung

```text
vmind purge DB --plan PLAN-ID (--backup ZIEL | --no-backup)
```

Vorbedingungen, sonst Abbruch ohne Änderung:

1. **Keine aktiven Clients.** MCP-Server, `serve`, Hooks und Skripte sind zu beenden;
   die Ausgabe fordert das ausdrücklich. SQLite kann ruhende Verbindungen nicht
   erkennen; durchgesetzt wird nur, dass während des Vorgangs niemand liest oder
   schreibt. Bekommt V-Mind die Sperre nicht innerhalb des Zeitlimits, bricht es ab.
   Ein Hook, der währenddessen schreiben will, scheitert an der Sperre; die
   Beobachtung geht verloren.
2. **Gültiger Plan** und unveränderter Dateiänderungszähler.
3. **Aktuelles Schema und `journal_mode=delete`.** Kein Checkpoint, keine
   Modusumstellung im Purge-Pfad.
4. **Ausdrückliche Sicherungsentscheidung** (siehe Sicherungs-Dilemma).

**Sperrhaltung:** Genau eine Verbindung mit `PRAGMA locking_mode=EXCLUSIVE` und
`PRAGMA secure_delete=ON` führt alle Schritte B bis E aus. Die exklusive Sperre wird
mit der ersten Schreibtransaktion erworben und erst beim Schließen der Verbindung nach
Schritt E freigegeben; zwischen den Schritten kann niemand lesen oder schreiben.

| Schritt | Inhalt | Zustand bei Abbruch genau hier |
| --- | --- | --- |
| A | Verbindung öffnen, Pragmas setzen, `BEGIN EXCLUSIVE`, Zähler mit Plan vergleichen | Datei unverändert |
| B | in derselben Transaktion: Felder redigieren, Rückzug, Prüfbefehle/-läufe/Beobachtungen löschen, `memories_fts` und `memories_trigram` mit `rebuild` neu aufbauen, Protokollzeile Status `redacted` | Rollback; das `-journal` enthält bis zum Rollback die alten Seiten; beim nächsten Öffnen stellt SQLite den alten Stand wieder her. Datei logisch unverändert, Geheimnis vorhanden |
| C | Commit (`synchronous=FULL`), danach Plan-Datei löschen | ab hier logisch entfernt; Reste können in freien Seiten liegen (durch `secure_delete` überschrieben) und in der gelöschten Journaldatei auf dem Datenträger |
| D | `VACUUM` (baut die Datei ohne freie Seiten neu) | VACUUM ist selbst atomar; bei Abbruch bleibt der Stand nach C |
| E | Transaktion: Protokollzeile Status `compacted`, Commit (`synchronous=FULL`), danach `fsync` des Ordners | vor dem Commit: Status bleibt `redacted`, `--finish` holt D und E nach; danach abgeschlossen |

Der letzte Statuscommit ist damit selbst dauerhaft gesichert; erst danach gilt der
Vorgang als `compacted`. `vmind purge DB --finish` führt D und E für alle Protokollzeilen
mit Status `redacted` aus, mit derselben Sperrhaltung, und ist wiederholbar. `doctor`
meldet offene `redacted`-Einträge.

### WAL-Datenbanken (spätere Erweiterung)

Version 1 bricht bei `journal_mode=wal` ab. Eine spätere Erweiterung braucht einen
eigenen, dokumentierten Offline-Vorbereitungsschritt außerhalb von `purge`
(vollständiger Checkpoint und bewusster Wechsel nach `delete`, mit eigener Prüfung), weil
der WAL-Modus den Dateiänderungszähler nicht verlässlich erhöht und alte Seiten in der
`-wal`-Datei hält. Nicht Teil dieses Entwurfs.

### Purge-Protokoll (neue Migration, Schema 7)

- Tabelle `purges(id, created_at, status, memories, journal, conversations, messages,
  checks, check_runs, observations)` mit `status IN ('redacted', 'compacted')` und je
  Namensraum nur der **Anzahl** der Ziele. Keine Zielidentitäten, keine Inhalte, keine
  Prüfsummen, kein Akteur-Freitext. `--finish` braucht keine Ziele.
- `memory_events.action` erhält zusätzlich `purged`, damit `show` erklärt, warum ein
  Eintrag nur noch den Platzhalter enthält. Die Migration folgt den üblichen Regeln
  (neue nummerierte Datei, Sicherung vor dem Upgrade). Offene Frage dazu: Blocker B2.

## Sicherungs-Dilemma

V-Mind sichert sonst vor jeder riskanten Änderung. Eine Sicherung vor einem Purge
enthält aber genau das Geheimnis, das entfernt werden soll. Deshalb:

- Kein stilles Backup. Der Aufruf verlangt `--backup ZIEL` oder `--no-backup`.
- Mit `--backup` wird wie bei `backup` geprüft gesichert, und die Ausgabe sagt deutlich:
  „Diese Sicherung enthält das Geheimnis. Nach Prüfung des Ergebnisses selbst löschen
  oder sicher verwahren.“
- Vorschau und Ausführung nennen nur die **Anzahl** bekannter Sicherungen je Herkunft
  (automatische Migrationssicherungen `*.before-schema-*.db` neben der Datei bzw. in
  `VMIND_BACKUP_DIR`). Dateipfade können selbst vertrauliche Bestandteile enthalten und
  erscheinen nur mit ausdrücklichem `--list-backups`, zusammen mit diesem Hinweis.
  Andere Kopien (manuelle Sicherungen, Synchronisationsdienste, Versionsverwaltung) kennt
  V-Mind nicht. V-Mind löscht keine Sicherung selbst.

## Nachweis und Grenzen

Nach Schritt E gilt als geprüft (und nur das):

- Keine V-Mind-Operation (`show`, `recall`, `search`, `journal`, `messages`, `resume`,
  `report`, MCP/JSONL) liefert das Geheimnis.
- `audit-secrets` meldet an den Zielen keinen Fund mehr.
- Die Bytes der Datenbankdatei enthalten den Wert nicht mehr (nur in Tests mit bekanntem
  Zufallsmarker prüfbar; in echten Daten wird der Wert nicht erneut verarbeitet).

Nicht geprüft und nicht versprochen:

- Physische Löschung auf SSDs und Copy-on-Write-Dateisystemen (btrfs, APFS, ZFS),
  Snapshots, Swap, Papierkorb.
- Gelöschte `-journal`-Dateien aus Schritt B und alte Dateiblöcke aus Schritt D.
- Sicherungen, Kopien, Protokolle von Hosts und Modellanbietern, Terminal-Verläufe.

## Abnahmematrix für eine spätere Umsetzung

Alle Tests mit einem **zur Laufzeit erzeugten Zufallsmarker**, der einer erkannten
Fundart entspricht; Testausgaben zeigen den Marker nie vollständig.

| Nr. | Fall | Erwartung |
| --- | --- | --- |
| 1 | Marker in jedem Feld jedes Namensraums, je ein Ziel | Nach Purge: keine Tabelle, kein `MATCH` in `memories_fts`/`memories_trigram`, keine V-Mind-Operation liefert ihn; nach VACUUM nicht in den Dateibytes; `audit-secrets` ohne Fund an den Zielen |
| 2 | Wie 1, Prüfung in **neuem Prozess** nach Wiederöffnen | gleiches Ergebnis |
| 3 | Kopie desselben Markers in einer anderen Zeile | Vorschau listet sie als vermutete Kopie; nach Purge nur der Ziele bleibt sie erhalten und `audit-secrets` findet sie |
| 4 | Vorschau | Datenbankdatei bytegleich vorher/nachher; Ausgabe ohne Marker |
| 5 | Ein Commit zwischen Vorschau und Ausführung | Zähler weicht ab: Abbruch, keine Änderung |
| 6 | Unbekannter Namensraum, fehlende ID, Dublette, Text-ID | Abbruch vor jeder Änderung |
| 7 | Anderer Prozess hält eine Lesetransaktion | Abbruch nach Zeitlimit, keine Änderung |
| 8 | Abbruch in Schritt B (Fehler im Test eingeschleust) | nach Wiederöffnen alter Stand, kein Protokolleintrag, Plan noch gültig |
| 9 | Prozess nach C, vor D beendet | Ziele redigiert, Protokoll `redacted`, Plan gelöscht, `doctor` meldet es, `--finish` führt D/E aus und setzt `compacted` |
| 10 | Prozess nach D, vor dem Statuscommit in E beendet | Status `redacted`; `--finish` erneut ausführbar, Ergebnis `compacted` |
| 11 | Validierter Eintrag als Ziel | danach zurückgezogen, nicht im Abruf als geprüft, keine Prüfbefehle mehr, `revalidate` führt nichts aus |
| 12 | Aufgabe mit mehreren Journalzeilen | `task:N` redigiert alle Zeilen einheitlich, jüngster Stand bleibt jüngster; `journal:N` ändert den Schlüssel nie |
| 21 | Datei zwischen Vorschau und Ausführung ausgetauscht oder zurückgespielt | Abbruch ohne Änderung (setzt Klärung von B6 voraus) |
| 13 | Ohne `--backup`/`--no-backup` | Abbruch ohne Änderung |
| 14 | Mit `--backup` | geprüfte Sicherung angelegt, Warnhinweis ausgegeben, Sicherung enthält den Marker (dokumentiertes Verhalten) |
| 15 | Altes oder fremdes Schema, fehlende Datei | Abbruch, nichts angelegt oder migriert |
| 16 | `journal_mode=wal` | Abbruch ohne Checkpoint und ohne Modusänderung |
| 17 | Alle Fehlermeldungen und Ausgaben (stdout, stderr, JSON) | enthalten weder Marker noch Teile davon noch Text-IDs noch Sicherungspfade (außer mit `--list-backups`) |
| 18 | Plan-Datei | Rechte 0600; enthält keinen Marker, keine Feldwerte, keine Hashes über Inhalte; nach C gelöscht; fremde oder veraltete Plan-ID abgewiesen |
| 19 | Purge-Protokoll | enthält nur Zeit, Status und Anzahlen |
| 20 | Gespräch als Ziel, danach VACUUM | Protokoll weiterhin korrekt; alter Plan nach VACUUM abgewiesen |

## Blocker vor einer Umsetzung

Diese Punkte müssen gemeinsam entschieden sein, bevor Code entsteht:

- **B1 Aufgabenschlüssel:** entschieden (#138): eigenes Ziel `task:N`, siehe
  [Aufgabenschlüssel](#aufgabenschlüssel).
- **B6 Änderungsnachweis des Plans:** Dateiänderungszähler und Bindung an die
  Datenbankidentität sind ungeprüfte Annahmen (siehe Plan); Prüfung vor Umsetzung.
- **B2 Schema 7:** Protokoll als eigene Migration wie oben, oder ohne Protokoll und
  `--finish` nur als „VACUUM erneut ausführen“? Vorschlag: Protokoll, weil `doctor` sonst
  einen abgebrochenen Purge nicht erkennen kann.
- **B3 Plan-Datei:** Ort neben der Datenbank (gleiche Rechte, gleicher Datenträger)
  oder eigenes Verzeichnis? Lebensdauer begrenzen (z. B. eine Stunde)?
- **B4 Kopiensuche:** Die interne Suche nach demselben Wert hält den Wert kurz im
  Speicher. Akzeptabel, solange er nie ausgegeben, protokolliert, gehasht oder
  gespeichert wird?
- **B5 `secure_delete`:** Das Systemwerkzeug `sqlite3` meldet hier `1`; im gebündelten
  SQLite wird es ausdrücklich gesetzt. Reicht das zusammen mit VACUUM?

## Bewusst nicht in Version 1

- Text-IDs von Gesprächen und Bereichsnamen: werden gemeldet („nicht entfernbar,
  Gespräch/Bereich neu anlegen“), nicht umgeschrieben.
- Ganze Gespräche auf einmal: zunächst nur `message:N` je Nachricht.
- WAL-Datenbanken: siehe oben.
