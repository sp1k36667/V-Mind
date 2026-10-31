# Entwurfsentscheidungen

V-Mind speichert Erfahrungen und liefert Wissen. Das Sprachmodell formuliert und
entscheidet selbst. Ein brauchbarer erster Stand braucht vor allem verlässliche
Herkunft, korrigierbares Wissen und eine gut testbare Abrufschnittstelle.

## Bausteine

- `vmind-core`: SQLite-Verbindung, atomare Migrationen, FTS5/BM25, Bereiche und Lebenszyklus.
- `vmind-cli`: menschliche Kommandozeile, JSON-Ausgabe, JSONL-Protokoll und Ollama-Testclient.
- `migrations`: unveränderte V1-Basis plus additive V2-Migration.

Der Kern kennt weder Gemma noch Ollama noch GPU-Treiber. Die KI-Schnittstelle ruft
auch ohne Modell dasselbe Gedächtnis ab. SQLite ist die dauerhafte Datenquelle;
ein späterer GPU-Index muss daraus wiederherstellbar bleiben und bei der Ausgabe
die aktuellen Status- und Bereichsfilter respektieren.

## Lebenszyklus

Erstellen speichert `pending`, Quelle und Erstellzeit. Validieren hinterlegt Prüfer
und Nachweis. Rückzug legt einen separaten Datensatz mit Akteur, Grund und Zeit an.
Ereignisse werden über SQLite-Trigger im selben Schreibvorgang protokolliert.
Wiederholtes Validieren/Rückziehen hat keine zusätzlichen Ereignisse zur Folge.
Zurückgezogene Inhalte werden nicht gelöscht, nicht automatisch wieder aktiviert
und auch aus der alten wörtlichen Suche ausgeschlossen.

Korrekturen erhalten neue IDs. Die Herkunft kann auf die alte ID verweisen. Es gibt
noch keine automatischen Zusammenführungen oder Entscheidungen bei widersprüchlichen
Aussagen. Gleiche Inhalte können mehrfach gespeichert werden.

## Abruf

FTS5 normalisiert Groß-/Kleinschreibung und Diakritika. Aus der Eingabe werden bis
zu 24 unterschiedliche alphanumerische Suchwörter gebildet, einfache deutsche und
englische Stoppwörter entfernt und die verbleibenden Wörter gequotet mit OR verknüpft.
Dadurch führen natürliche Fragen eher zu Treffern als eine komplette wörtliche Phrase.
FTS-Spezialsyntax aus der Eingabe wird nicht ausgeführt. BM25 bewertet das Problemfeld
mit Gewicht 2 und die Lösung mit Gewicht 1. Bei gleichem Rang entscheidet die ID.

Diese einfache Wortsuche ist transparent und benötigt kein Embeddingmodell.
Eine Trefferliste beweist keine inhaltliche Relevanz. Der Aufrufer erhält vollständige
Quellen und Nachweise für seine eigene Bewertung. Ein späteres Ranking sollte an
einem echten, von Menschen bewerteten Fehlerkorpus gemessen werden.

## Datenbankverhalten

Beim Öffnen wird die Version gelesen. Schema 3 benötigt keine Schreibtransaktion.
Bei einer Migration sperrt eine kurze IMMEDIATE-Transaktion konkurrierende Schreiber,
prüft die Version erneut und führt alle nötigen Änderungen gemeinsam aus. Bei Fehlern
rollt die gesamte Migration zurück. Unbekannte neuere Versionen werden abgelehnt.

FTS wird beim Upgrade aus den bestehenden Daten aufgebaut und danach über Trigger
aktualisiert. Suchergebnisse filtern stets auf validierte, nicht zurückgezogene
Einträge aus dem Projektbereich oder global. Fremdschlüssel sind eingeschaltet;
der Busy-Timeout beträgt fünf Sekunden. Kein WAL-Zwang auf dem Code2-Laufwerk.

Der Erstimport protokolliert `imported`, weil V1 keinen Prüfzeitpunkt gespeichert hat.
Echte historische Zeitpunkte werden nicht nachträglich erfunden. Datenbank-Backups
gehören nicht ins öffentliche Repository.

## Lernen über Läufe

Die Kernidee ist eine Lernschleife ohne Training: Ein Modell findet über echtes
Testfeedback einen Fehler, behebt ihn und schlägt die Erfahrung („Fehler X →
Lösung Y“) als `pending` vor. Gültig wird sie erst, wenn eine Prüfung sie bestätigt,
idealerweise derselbe Test, der den Fehler gefunden hat. Spätere Läufe rufen die
Erfahrung ab und vermeiden den Fehler von Anfang an.

Stand: Der E2B-Pilot zeigt die Wiederverwendung geprüften Wissens eines anderen
Modells (`docs/experiments/e2b-pilot.md`). Die vollständige Schleife mit selbst
gefundenen und testbasiert bestätigten Erfahrungen ist noch nicht experimentell
gezeigt; dafür sind Prüfbefehle am Eintrag und ein Lernkurven-Experiment geplant.

## Abgrenzung zu ähnlichen Ansätzen

Die Idee, dass Sprachmodelle ohne Training aus Erfahrung lernen, ist nicht neu.
Bekannte Arbeiten und Werkzeuge, so wie wir sie verstehen:

- **Reflexion** (Shinn u. a., 2023): Das Modell formuliert nach Fehlschlägen
  sprachliche Lehren und nutzt sie in weiteren Versuchen derselben Aufgabe.
- **Voyager** (Wang u. a., 2023): Ein Minecraft-Agent baut eine Bibliothek aus
  ausführbaren Fähigkeiten auf; aufgenommen wird nach Umgebungsfeedback und einer
  Selbstprüfung durch das Modell. Konzeptionell der nächste Verwandte.
- **ExpeL** (Zhao u. a., 2023): Erkenntnisse werden aus erfolgreichen und
  gescheiterten Versuchen abgeleitet und später abgerufen.
- **mem0, Letta (MemGPT)** und eingebaute Memory-Funktionen von KI-Assistenten:
  allgemeine Gedächtnisschichten, die speichern, was das Modell für relevant hält.
- **RAG** allgemein: Abruf aus Dokumentensammlungen, ohne eigenen Prüfstatus pro Aussage.

V-Mind unterscheidet sich in der Kombination:

| | Übliche Ansätze | V-Mind |
|---|---|---|
| Wer entscheidet, ob eine Erfahrung gilt? | meist das Modell selbst | eine externe Prüfung mit Nachweis |
| Ungeprüfte Erfahrung | wird meist direkt genutzt | bleibt `pending`, wird nie abgerufen |
| Falsches oder Veraltetes | oft unbemerkt, teils überschrieben | Rückzug mit Grund, Historie bleibt |
| Herkunft | oft unklar | Pflichtfeld bei jedem Eintrag |
| Modellbindung | oft ein bestimmtes System | modellunabhängig: MCP, CLI, JSONL, Ollama |
| Betrieb | häufig Forschungsprototyp oder Cloud-Dienst | eine lokale SQLite-Datei |

Kurz: Andere Systeme merken sich, was das Modell glaubt. V-Mind merkt sich, was
nachweislich funktioniert hat. Die genannten Arbeiten lösen teils andere Probleme
(z. B. Lernen innerhalb einer Aufgabe oder in einer Spielwelt); der Vergleich soll
die Unterschiede einordnen, nicht deren Ergebnisse bewerten.

## Spezialisierung kleiner lokaler Modelle

Ein kleines, allgemeines Modell kann mit einer fachlichen V-Mind-Datenbank als
Spezialist arbeiten, ohne Training. Beispiel Wissenschaft: Methoden, Formeln,
bekannte Fallstricke, geprüfte Messwerte und Literaturangaben, jeweils mit Quelle
und Prüfnachweis.

Vorteile gegenüber Feinabstimmung:

- kein Training und keine Trainingshardware; das Modell bleibt austauschbar,
- Wissen lässt sich jederzeit ergänzen, korrigieren und zurückziehen,
- jede Antwortgrundlage ist auf eine Quelle zurückführbar, in der Wissenschaft zentral,
- Daten bleiben lokal.

Grenzen, die dabei beachtet werden müssen:

- Das Modell erhält Wissen, keine neue Denkfähigkeit. Schwieriges Schlussfolgern
  bleibt durch das Modell begrenzt.
- Der Nutzen hängt am Abruf: Fachbegriffe, Synonyme und Formelschreibweisen
  findet die heutige Wortsuche (FTS5) schlecht; semantische Suche ist dafür nötig.
- Der Kontext kleiner Modelle ist knapp (E2B: 8.192 Tokens); Einträge müssen
  kurz und präzise sein.
- „Validiert“ braucht fachlich passende Nachweise: ein reproduzierbares Skript oder
  eine Rechnung, eine geprüfte Quelle mit DOI und Fundstelle, ein Messprotokoll.
  Code-Tests sind dafür nur ein Sonderfall.

Stand: Hypothese, noch nicht getestet. Ein Prüfversuch wäre ein fachlicher
Fragenkatalog mit bekannten Antworten, beantwortet von demselben kleinen Modell
mit und ohne fachliche V-Mind-Datenbank.

## Bewusst offen

Noch keine produktionsreife Zugriffskontrolle, Manipulationssicherheit, Verschlüsselung,
automatische Wahrheitsprüfung, automatische Anbindung an Codex, Embeddings oder
GPU-residente Suche. Ein MCP-Server (`vmind mcp DB`) bildet die JSONL-Operationen
als Werkzeuge ab; er ist ein Adapter in `vmind-cli`, kein Teil des Kerns.
Die ersten nächsten Schritte sind reale Fehlerfälle, Bewertung der Abrufqualität
und daraus abgeleitete Suchverbesserungen. ROCm bleibt unverändert.

## Projekt- und Gesprächsgedächtnis (Schema 3)

`project_journal` ist ein append-only Arbeitsprotokoll: Ziel, Aufgabe, Entscheidung,
nächster Schritt oder Notiz. Aufgaben haben einen stabilen Schlüssel. Der jüngste
Eintrag je Schlüssel bestimmt den aktuellen Status; ältere Einträge bleiben erhalten.
Ziel und nächster Schritt verwenden jeweils den jüngsten Eintrag. Entscheidungen
werden nicht automatisch verworfen oder zusammengefasst.

`conversations` und `chat_messages` speichern Gespräche vollständig in SQLite.
`ask` setzt das Standardgespräch `default:BEREICH` fort; separate Gespräche erhalten
zufällige IDs. Die Frage wird vor dem Modellaufruf gespeichert. Nur erfolgreiche
Antworten erhalten die Rolle assistant. Ein Fehler wird als tool-Nachricht hinterlegt.
Ein Prozessabbruch während der Generierung kann eine unbeantwortete Nutzerfrage
hinterlassen; sie bleibt lesbar. Ein erzeugter, noch nicht gespeicherter Antworttext
kann bei einem abrupten Abbruch verloren gehen.

`resume` liest einen konsistenten Snapshot in einer Lesetransaktion. Er enthält
begrenzte Listen samt Gesamtzahlen. `journal` und `messages` erlauben das vollständige
Nachlesen per monotonem ID-Cursor. Keine älteren Einträge werden wegen des
Kontextlimits gelöscht. Projektkontext bleibt exakt bereichsgebunden, ohne globale
Beigemischung. Direkter Zugriff auf Gesprächs-IDs ist wie bei Wissens-IDs keine
Zugriffskontrolle. Externe Clients können mit `message` Gesprächsteile importieren;
Rollen und Texte sind Berichte des Clients, keine Authentizitätsgarantie.

Das Modell erhält lediglich einen begrenzten Ausschnitt. Für zuverlässige Fortsetzung
müssen Klienten Fortschritt mit Quellen melden und bei Bedarf ältere Ereignisse lesen.
Es gibt keine automatische semantische Zusammenfassung oder Überwachung fremder Apps.
Mehrere Prozesse dürfen dieselbe Datenbank öffnen; parallele Modellantworten innerhalb
desselben Gesprächs müssen vom Client serialisiert werden. Noch keine Gesprächssperre.
