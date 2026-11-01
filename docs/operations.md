# Sicherung, Diagnose und Upgrade

Diese Befehle gehören zum Entwicklungsstand nach 0.2.0. Sie sind im veröffentlichten
0.2.0-Binary noch nicht enthalten. Ein erfolgreicher Prüfbefehl bestätigt seinen
Testgegenstand, nicht automatisch die Wahrheit einer beliebigen Erklärung.

## Diagnose ohne Änderung

```sh
vmind --json doctor vmind.db
```

Öffnet ausschließlich eine vorhandene Datenbank zum Lesen. Keine neue Datei, keine
Migration, kein Eintrag im Tagebuch. Prüft SQLite-Integrität, Fremdschlüssel,
unterstützte Schemaversion und erforderliche Tabellen/Trigger. Bei Fehlern ist der
Exit-Code ungleich null. `healthy: true` mit `migration_required: true` bedeutet:
Die ältere unterstützte Datenbank ist strukturell in Ordnung, braucht aber ein Upgrade.
Eine neuere unbekannte Version wird nicht als gesund/kompatibel bezeichnet.

Dies ist keine fachliche Prüfung der Inhalte und kein Schutz gegen gezielte
Manipulationen. Auch die vollständige inhaltliche Synchronisierung der FTS-Indizes
wird damit nicht nachgewiesen. Fehlende Schreibrechte, ein defekter MCP-Client oder
Ollama werden von dieser Datenbankdiagnose nicht getestet. Bei WAL-Datenbanken
kann selbst ein Lesezugriff beschreibbare vorhandene `-shm`/`-wal`-Dateien oder ein
geeignetes Verzeichnis benötigen; ein Fehler dabei ist kein Beweis für kaputte Daten.
Eine aktive WAL-Datenbank nicht durch Weglassen dieser Dateien scheinbar reparieren.

## Konsistente Sicherung

```sh
vmind --json backup vmind.db vmind-sicherung.db
```

Die SQLite-Backup-API erzeugt einen konsistenten Snapshot einschließlich gespeicherter
WAL-Daten. Das Original bleibt unverändert; ältere Schemata werden nicht migriert.
Das Ziel muss neu sein: Auch leere vorhandene Dateien und Verknüpfungen werden nicht
überschrieben. Unter Unix wird die neue Sicherung mit Rechten 0600 angelegt.
Unter Windows gelten die Zugriffsregeln des Zielordners.

Erfolg (`verified: true`, Exit 0) gibt es erst nach Integritäts-, Fremdschlüssel- und
Strukturprüfung sowie Bestätigung des Dateiinhalts an das Betriebssystem. Eine vom
Programm als fehlerhaft erkannte Sicherung wird entfernt. Nach Stromausfall oder
Prozessabbruch kann eine unvollständige Zieldatei übrig bleiben: vor Verwendung mit
`doctor` prüfen, niemals allein anhand ihres Vorhandenseins als fertig betrachten.

Sicherungen enthalten dieselben vertraulichen Informationen wie das Original.
Geschützt und möglichst auf einem zweiten Datenträger aufbewahren; ein Snapshot auf
demselben Laufwerk schützt nicht vor dessen Ausfall. Freier Platz ist Voraussetzung.
Sehr lange gesperrte oder große Sicherungen können am Zeitlimit von 30 Sekunden
scheitern; dann wird kein Erfolg gemeldet.

## Automatische Sicherung vor Schemaänderungen

Vor der Migration einer vorhandenen Dateidatenbank mit Schema 1 bis 4 wird daneben
eine geprüfte Sicherung `DB.before-schema-5-ZEIT-PID.db` erstellt. Der Pfad wird auf
stderr ausgegeben (JSON/MCP-stdout bleibt sauber). Die Migration hält dabei ihre
Schreibsperre; der Snapshot entsteht über eine separate rein lesende Verbindung.
Scheitert die Sicherung, findet kein Upgrade statt. Auch die Migration selbst bleibt
atomar. In-Memory-Datenbanken brauchen keine Dateisicherung; neue leere Datenbanken
werden direkt initialisiert. Automatische Sicherungen werden nicht still gelöscht. Nach geprüftem Upgrade und
getesteter Wiederherstellung können alte Sicherungen bewusst selbst entfernt werden.
Mindestens eine unabhängige geprüfte Rückfallkopie behalten.

Schreibrecht im Quellordner und genügend Platz für die Sicherung sind erforderlich.
Das ist eine bewusste Voraussetzung für ein automatisches Upgrade. Mit
`VMIND_BACKUP_DIR` lässt sich ein anderer vorhandener Sicherungsordner verwenden,
beispielsweise auf einem zweiten Datenträger. Ein leerer Wert ist ein Fehler und
überspringt die Sicherung nicht. Bei fehlendem Platz/Rechten bleibt das Upgrade
abgebrochen und die Fehlermeldung nennt diese Abhilfe. Das Datenbankverzeichnis
braucht für SQLite-Journal und Upgrade selbst weiterhin geeignete Schreibrechte
und Platz. Auch `vmind backup DB ANDERER_PFAD` ist zur unabhängigen Sicherung möglich;
eine solche Kopie deaktiviert die automatische Sicherung nicht. Eine fehlgeschlagene
Migration kann eine gültige Sicherung zurücklassen; deren Vorhandensein bedeutet
nicht, dass die Migration abgeschlossen ist.

## Wiederherstellung und Versionswechsel

1. Alle Clients dieser Datenbank beenden oder trennen, einschließlich MCP und Skripten.
2. Die Sicherung mit einem passenden Binary und `doctor` prüfen.
3. Eine Kopie der Sicherung unter einem neuen Pfad verwenden. Nicht in eine geöffnete
   Datenbank hineinkopieren und nicht nur die Hauptdatei einer aktiven WAL-Datenbank ersetzen.
4. Mit einer zur Sicherung passenden V-Mind-Version öffnen; eine neue Version kann
   die ältere Kopie nach automatischer Sicherung migrieren.
5. `doctor`, `stats`, `resume` und eine bekannte Wissensabfrage prüfen. Erst dann die
   Clientkonfiguration auf den geprüften Pfad umstellen und neu verbinden.

Ein altes Binary kann ein neueres Schema nicht öffnen. Ein schon laufender alter
MCP-Prozess muss ausdrücklich neu gestartet werden; ein Austausch der Programmdatei
ersetzt nicht den Code im Speicher. Eine Sicherung ist keine Garantie für ein
funktionsfähiges Restore: diesen Ablauf mit eigenen Daten regelmäßig an einer Kopie
prüfen.


## Dateinamen und SQLite-URIs

CLI-Befehle, MCP/JSONL-Server, Hooks und Wartungsfunktionen behandeln DB-Argumente
immer als Dateipfade. Ein Name wie `file:projekt.db?mode=memory` wird nicht als
flüchtige SQLite-Datenbank oder als Umleitung interpretiert. Leere Dateipfade sind
Fehler; auch `:memory:` ist in der CLI ein Dateiname (auf Systemen, die ihn erlauben).
Für Rust-Bibliotheksnutzer bleibt die ausdrücklich gewählte SQLite-Semantik von
`MemoryStore::open` bestehen; für persistente Nutzereingaben `open_file` bzw. die
Datei-Öffner verwenden. `MemoryStore::in_memory` bleibt für Tests verfügbar.
