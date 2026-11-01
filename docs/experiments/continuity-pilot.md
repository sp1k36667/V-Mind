# Fortsetzungspilot mit Gemma 4 12B: Kriterien nicht erfüllt

Ausgeführt am 1. November 2026. Eingefrorener Plan und Harness:
`be01ee67cef2f54efe284f0b030707ce390d9685`.
[Vorabplan](continuity-pilot-plan.md), [vollständige synthetische Rohdaten](data/continuity-20261101/results.jsonl),
[Modell-Digest und Programm-Hashes](data/continuity-20261101/metadata.json).
45 Aufrufe wurden einmalig ausgeführt; kein Versuch ersetzt oder repariert.

## Was verglichen wurde

Drei synthetische Projektstände, drei Darstellungen, fünf Seeds. N erhält keine
Historie. M erhält eine automatisch aus genau demselben Snapshot erzeugte flache
Markdown-Feldliste. V erhält den rohen JSON-resume-Snapshot. **M ist keine von einem
Menschen erstellte Übergabe** und hat keinen Wissensvorsprung gegenüber V.
Dies ist ein Darstellungs-/Fortsetzungspilot, kein Test einer allgemeinen Lernwirkung.
Der Testhost lädt Daten; das Modell benutzt hier keine MCP-Werkzeuge. Auch der
Ollama-Adapter von `vmind ask` wird nicht ausgeführt; seine zusätzliche Startanweisung
und eigene Kürzung sind daher nicht Gegenstand dieses Piloten.

Jeder Aufruf beantwortet elf Fragen: acht verfügbare Fakten, zwei unbekannte Angaben
und eine absichtlich nur in der älteren Historie enthaltene Portnummer. Die Portnummer
fehlt in beiden Snapshotdarstellungen. Ihr tatsächlicher Wert wäre nur über weiteres
Nachlesen verfügbar. Deshalb sind ohne Raten höchstens 150/165 Punkte erreichbar.
135/165 im vorab festgelegten Kriterium entspricht 90 % dieses erreichbaren Maximums.

## Ergebnis nach unveränderten Regeln

| Messgröße | N | M | V |
|---|---:|---:|---:|
| Richtige Antworten (von 165) | 6 | 133 | 117 |
| Acht verfügbare Fakten richtig (von 120) | 0 | 108 | 93 |
| Tatsächlich unbekannte Angaben korrekt erkannt (von 30) | 6 | 25 | 24 |
| Alte Archiv-Portnummer wiederhergestellt (von 15) | 0 | 0 | 0 |
| Archiv-Portnummer ehrlich als unbekannt angegeben (von 15) | 0 | 14 | 15 |
| Antwortfehler beim JSON-Parsen | 9 | 1 | 0 |
| Exakt gefordertes Antwortformat (von 15) | 0 | 0 | 0 |

Die zusätzlichen Formatfehler erfolgreicher JSON-Antworten sind unter anderem
überzählige Felder wie `password_2` oder `unknown_date`. Ein parsebarer JSON-Text ist
nicht dasselbe wie ein eingehaltenes Schema. Fehlende Felder zählen als falsch.
Die Erfindungszählung bei den beiden unbekannten Angaben war jeweils null; das
bedeutet **nicht** fehlerfreie Antworten: Fehlende Felder und Parsefehler werden
separat gezählt und können nicht als korrektes Unwissen ausgelegt werden.

Alle Punkte außer dem Vorteil gegenüber leerem Kontext verfehlen die Pilotgrenzen:
V bleibt unter 135 richtigen Antworten, erkennt weniger als 29 der unbekannten Angaben,
liegt 16 statt höchstens 5 Punkte unter M und hat 15 Formatabweichungen.
Die acht verfügbaren Fakten liegen mit 77,5 % deutlich über N (0 %), aber **nicht über
M (90 %)**. Daraus folgt kein Vorteil gegenüber einer gleichwertigen Textübergabe.

## Welche Fragen scheiterten

Je Spalte und Frage 15 Antworten. Exakte Bewertung mit lediglich entferntem äußerem
Leerraum; Groß-/Kleinschreibung, Satzzeichen und zusätzliche Wörter werden nicht
nachträglich normalisiert.

| Frage | N | M | V |
|---|---:|---:|---:|
| release | 0 | 14 | 15 |
| folder | 0 | 14 | 5 |
| backend | 0 | 11 | 7 |
| schema | 0 | 14 | 15 |
| search | 0 | 14 | 15 |
| next | 0 | 13 | 6 |
| assistant | 0 | 14 | 15 |
| gpu | 0 | 14 | 15 |
| archive_port | 0 | 0 | 0 |
| password | 3 | 14 | 15 |
| production_date | 3 | 11 | 9 |


## Fehleranalyse und Produktfolgen

- **Aktueller nächster Schritt:** V nannte mehrfach `old-packaging` statt des aktuellen
  `negative-cases-N`. Der Snapshot enthält alte next_step-Ereignisse unter recent_events
  neben dem aktuellen next_step. Das ist ein konkreter Ansatz zur Verbesserung:
  aktuelle Zustände und frühere Zustandsversionen klar trennen; vollständige Historie
  weiterhin über journal verfügbar halten.
- **Darstellung:** Gleiche Informationen als Feldliste funktionierten hier besser als
  verschachteltes JSON. Das legt eine optionale lesbare Übergabe nahe, beweist aber
  keinen allgemeinen Formatvorteil für andere Modelle oder Projekte.
- **Strenge Bewertung:** Nicht jeder Punktverlust ist ein falscher Sachverhalt.
  Beispielsweise ist „Backend SQLite statt PostgreSQL“ sachlich passend, entspricht aber
  nicht dem geforderten exakten Wert „SQLite“. Diese Bewertungsgrenze war vorab festgelegt
  und bleibt unverändert. Der Bericht darf die strenge Quote nicht als reine
  Halluzinationsquote verkaufen.
- **Kontextlücke:** Kein Snapshot kann Daten wiedergeben, die er nicht enthält.
  V meldete die fehlende Archiv-Portnummer in allen 15 Aufrufen als unbekannt.
  Ein eigener Werkzeugtest muss zeigen, ob ein Client ältere Details tatsächlich findet.

## Aufwand und Grenzen

Gemma-4-12B Q4_0, Temperatur 0,7, 8192 Kontext, maximal 512 Ausgabetokens, Seeds
3101–3105, Bedingungen je Projekt/Seed permutiert, keep_alive 0. Kumulierte gemessene
Laufzeit: N 147,3 s, M 151,4 s, V 121,0 s. Diese lokalen Kaltstartmessungen sind
kein allgemeiner Geschwindigkeitsnachweis. Nicht abgebrochene JSON-Antworten können
sich deutlich in ihrer Länge unterscheiden. Alle Antwort- und Promptmetriken stehen
in den Rohdaten.

Drei gleichartig konstruierte Projekte und fünf Seeds sind keine repräsentative
Stichprobe realer Entwicklungsprojekte. Keine Signifikanz- oder
Nichtunterlegenheitsbehauptung. Das negative Ergebnis bleibt veröffentlicht.
Ein weiterer Versuch benötigt eigene vorab festgelegte Regeln und neue Seeds.
