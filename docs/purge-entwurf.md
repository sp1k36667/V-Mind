# Entwurf: gezieltes Entfernen von Geheimnissen (`purge`)

Status: **Entwurf zur gemeinsamen Prüfung, nicht umgesetzt.** Grundlage sind die
Abstimmungen im Teamkanal (#116, #120, #121, #131) und das lesende Audit
`vmind audit-secrets` (PR #29). Dieses Dokument legt fest, was ein späterer Befehl tun
darf und wie das geprüft wird. Es verspricht keine physische Löschung.

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
- Keine Änderung an Bereichsnamen (`scope`) in Version 1 (siehe offene Fragen).

## Ziele (Namensräume)

Jedes Ziel ist `NAMENSRAUM:ID` mit numerischer ID, so wie `audit-secrets` sie meldet.
Unbekannte Namensräume, nicht vorhandene IDs, Dubletten oder nichtnumerische IDs führen
zum Abbruch **vor** jeder Änderung.

| Ziel | Tabelle (Schlüssel) | Was entfernt wird |
| --- | --- | --- |
| `memory:N` | `memories.id` | problem, solution, source, validated_by, evidence des Eintrags; dazu alle Zeilen in `memory_events` (actor, reason) und `invalidations` (actor, reason) dieses Eintrags; alle `memory_checks` und deren `check_runs` des Eintrags werden gelöscht |
| `journal:N` | `project_journal.id` | body, source; task_key wird durch `purged-N` ersetzt (siehe Folgen) |
| `conversation:R` | `conversations.rowid` | title (die Text-ID bleibt; siehe offene Fragen) |
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
damit `check`/`revalidate` nie einen redigierten Befehl ausführen.

**Folgen für Aufgaben:** Ein redigierter `task_key` trennt dieses Ereignis von der
Aufgabe. `resume` zeigt dann ggf. einen älteren Stand als aktuell. Die Vorschau weist
darauf hin; die Nutzerin oder der Nutzer kann danach mit `task` einen neuen Stand
eintragen.

**Kopien in anderen Zeilen** gehören nicht zum Ziel. Die Vorschau sucht intern nach
denselben erkannten Werten in allen Feldern, die das Audit kennt, und listet
Fundstellen außerhalb der Ziele als **„vermutete Kopie, nicht im Auftrag“** mit
Namensraum und ID. Sie werden nur entfernt, wenn sie ausdrücklich als weiteres Ziel
genannt werden. Kopien, die keine bekannte Fundart enthalten oder umformuliert sind,
findet die Vorschau nicht; das steht in jeder Vorschau.

## Ablauf

### 1. Vorschau (rein lesend)

```text
vmind purge DB --preview ZIEL [ZIEL ...]
```

- Öffnet wie `audit-secrets` nur lesend in einem Snapshot; legt nichts an, migriert nicht.
- Verlangt das aktuelle Schema; sonst Hinweis auf `doctor`, `backup` und Upgrade.
- Ausgabe nur mit festen Bezeichnern und Zahlen: je Ziel die betroffenen Tabellen,
  Feldnamen und Zeilenzahlen, die Folgen (Rückzug, gelöschte Prüfbefehle, getrennte
  Aufgabe), vermutete Kopien, bekannte Sicherungsdateien (siehe unten) und eine
  **Bestätigungskennung**. Nie Feldwerte, Ausschnitte oder Text-IDs.
- Bestätigungskennung: Prüfsumme über die sortierten Ziele und den aktuellen Inhalt aller
  betroffenen Zeilen. Ändert sich bis zur Ausführung irgendetwas, passt sie nicht mehr.

### 2. Ausführung

```text
vmind purge DB --confirm KENNUNG (--backup ZIEL | --no-backup) ZIEL [ZIEL ...]
```

Vorbedingungen, sonst Abbruch ohne Änderung:

1. **Keine aktiven Clients.** MCP-Server, `serve`, Hooks und Skripte sind zu beenden;
   die Ausgabe fordert das ausdrücklich. SQLite kann ruhende Verbindungen nicht
   erkennen; durchgesetzt wird nur, dass während des Vorgangs niemand liest oder
   schreibt: `PRAGMA locking_mode=EXCLUSIVE` und eine `EXCLUSIVE`-Transaktion. Bekommt
   V-Mind die Sperre nicht innerhalb des Zeitlimits, bricht es ab. Ein Hook, der
   währenddessen schreiben will, scheitert an der Sperre; die Beobachtung geht verloren.
2. **Gleiche Ziele und Kennung wie in der Vorschau.**
3. **Aktuelles Schema** und `journal_mode` `delete` (V-Mind-Standard). Steht die Datei
   auf `wal`, muss vorher `PRAGMA wal_checkpoint(TRUNCATE)` vollständig gelingen,
   sonst Abbruch.
4. **Ausdrückliche Sicherungsentscheidung** (siehe Sicherungs-Dilemma).

Schritte:

| Schritt | Inhalt | Zustand bei Abbruch genau hier |
| --- | --- | --- |
| A | `PRAGMA secure_delete=ON` für die Verbindung, Sperre holen, Kennung erneut berechnen | Datei unverändert |
| B | in **einer** Transaktion: Felder redigieren, Rückzug, Prüfbefehle/-läufe/Beobachtungen löschen, `memories_fts` und `memories_trigram` mit `rebuild` neu aufbauen, Protokollzeile Status `redacted` | Rollback; das `-journal` enthält bis zum Rollback die alten Seiten; beim nächsten Öffnen stellt SQLite den alten Stand wieder her. Datei logisch unverändert, Geheimnis vorhanden |
| C | Commit | ab hier logisch entfernt |
| D | `VACUUM` (baut die Datei neu, ohne freie Seiten) | VACUUM ist selbst atomar; bei Abbruch bleibt der Stand nach C. Reste können in freien Seiten und im gelöschten Journal auf dem Datenträger liegen |
| E | Datei und Ordner mit `fsync` bestätigen, Protokollzeile Status `compacted` | wie D |

`vmind purge DB --finish` holt D und E für alle Protokollzeilen mit Status `redacted`
nach. `doctor` meldet offene `redacted`-Einträge.

### Purge-Protokoll (neue Migration, Schema 7)

- Tabelle `purges(id, created_at, target_count, status)` mit `status IN ('redacted',
  'compacted')`, und `purge_targets(purge_id, namespace, target_id)`. Keine Inhalte,
  keine Prüfsummen über Inhalte (sie könnten kurze Geheimnisse bestätigen), kein
  Akteur-Freitext.
- `memory_events.action` erhält zusätzlich `purged`, damit `show` erklärt, warum ein
  Eintrag nur noch den Platzhalter enthält. Die Migration folgt den üblichen Regeln
  (neue nummerierte Datei, Sicherung vor dem Upgrade).

## Sicherungs-Dilemma

V-Mind sichert sonst vor jeder riskanten Änderung. Eine Sicherung vor einem Purge
enthält aber genau das Geheimnis, das entfernt werden soll. Deshalb:

- Kein stilles Backup. Der Aufruf verlangt `--backup ZIEL` oder `--no-backup`.
- Mit `--backup` wird wie bei `backup` geprüft gesichert, und die Ausgabe sagt deutlich:
  „Diese Sicherung enthält das Geheimnis. Nach Prüfung des Ergebnisses selbst löschen
  oder sicher verwahren.“
- Vorschau und Ausführung listen bekannte Sicherungen mit Pfad: automatische
  Migrationssicherungen `*.before-schema-*.db` neben der Datei und in
  `VMIND_BACKUP_DIR`. Andere Kopien (manuelle Sicherungen, Synchronisationsdienste,
  Versionsverwaltung) kennt V-Mind nicht. V-Mind löscht keine Sicherung selbst.

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
| 4 | Vorschau | Datei bytegleich vorher/nachher; Ausgabe ohne Marker |
| 5 | Inhalt zwischen Vorschau und Ausführung geändert | Abbruch, keine Änderung |
| 6 | Unbekannter Namensraum, fehlende ID, Dublette, Text-ID | Abbruch vor jeder Änderung |
| 7 | Anderer Prozess hält eine Lesetransaktion | Abbruch nach Zeitlimit, keine Änderung |
| 8 | Abbruch in Schritt B (Fehler im Test eingeschleust) | nach Wiederöffnen alter Stand, kein Protokolleintrag |
| 9 | Prozess nach C, vor D beendet | Ziele redigiert, Protokoll `redacted`, `doctor` meldet es, `--finish` führt D/E aus und setzt `compacted` |
| 10 | Validierter Eintrag als Ziel | danach zurückgezogen, nicht im Abruf als geprüft, keine Prüfbefehle mehr, `revalidate` führt nichts aus |
| 11 | Journal-Aufgabe als Ziel | Vorschau nennt die Trennung von der Aufgabe; `resume` danach ohne Marker |
| 12 | Ohne `--backup`/`--no-backup` | Abbruch ohne Änderung |
| 13 | Mit `--backup` | geprüfte Sicherung angelegt, Warnhinweis ausgegeben, Sicherung enthält den Marker (dokumentiertes Verhalten) |
| 14 | Altes oder fremdes Schema, fehlende Datei | Abbruch, nichts angelegt oder migriert |
| 15 | `journal_mode=wal` mit nicht vollständig möglichem Checkpoint | Abbruch ohne Änderung |
| 16 | Alle Fehlermeldungen und Ausgaben (stdout, stderr, JSON) | enthalten weder Marker noch Teile davon noch Text-IDs |
| 17 | Purge-Protokoll | enthält nur Namensraum, numerische ID, Zeit und Status |

## Offene Fragen zur gemeinsamen Entscheidung

1. **Text-IDs und Bereichsnamen:** Ein Geheimnis in `conversations.id` oder in einem
   `scope` lässt sich nicht redigieren, ohne Verweise umzuschreiben. Vorschlag: in
   Version 1 nur melden („nicht entfernbar, Gespräch/Bereich neu anlegen“).
2. **Ganze Gespräche:** Reicht `message:N` je Nachricht, oder braucht es
   `conversation:R --all-messages`? Vorschlag: zunächst nicht, Vorschau pro Nachricht.
3. **Kopiensuche:** Die interne Suche nach demselben Wert hält den Wert kurz im
   Speicher. Akzeptabel, solange er nie ausgegeben, protokolliert oder gespeichert wird?
4. **`secure_delete`:** Das Systemwerkzeug `sqlite3` meldet hier `1`; für das
   gebündelte SQLite wird es explizit gesetzt. Reicht das zusammen mit VACUUM, oder
   zusätzlich `PRAGMA incremental_vacuum` vermeiden?
5. **Schema 7:** Eigene Migration nur für das Protokoll, oder Protokoll weglassen und
   den Zustand `redacted` nur über Platzhaltertexte erkennen? Vorschlag: Protokoll,
   weil `--finish` und `doctor` sonst Textmuster suchen müssten.
