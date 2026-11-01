# Synthetischer Fortsetzungspilot – vorab festgelegter Plan

Status: vor erstem gezählten Modelllauf eingefroren. Maßgeblich ist der Commit mit
Plan und `examples/continuity/run.py`; dessen Hash wird im Ergebnisbericht genannt.
Kein Nachtrainieren, kein Lernkurvenexperiment und keine allgemeine Produktabnahme.

## Frage und Bedingungen

Kann ein frischer Aufruf des vorhandenen lokalen Gemma-4-12B-Modells bekannte
Projektinformationen aus einem automatisch geladenen V-Mind-Snapshot korrekt
wiedergeben und fehlende Informationen als unbekannt erkennen?

- N: kein Projektverlauf, nur Fragen und dieselben Antwortanweisungen.
- M: eine kopierbare Markdown-Übergabe mit exakt denselben Feldwerten wie V. Sie wird
  aus demselben Snapshot erstellt, keine zusätzliche Zusammenfassung oder Korrektur.
- V: `resume`-Snapshot aus einer neu aufgebauten V-Mind-Testdatenbank als JSON.

M ist ein Vergleich der Darstellungsformen mit gleichwertiger Information, keine
Messung der menschlichen Arbeitszeit beim Erstellen einer Übergabe. V wird vom
Testhost geladen; das Modell benutzt in diesem Pilot keine MCP-Werkzeuge. Ein
späterer echter Werkzeugtest ist gesondert erforderlich.

## Material und Durchführung

Drei synthetische Projekte, jeweils Ziel, sechs Aufgaben mit Statuswechseln,
24 Verlaufsnotizen, fünf Entscheidungen einschließlich ausdrücklich ersetzter
Backendentscheidung, drei nächste Schritte und eine gespeicherte Assistentenantwort.
Elf eingefrorene Fragen pro Projekt: acht im Snapshot verfügbare Fakten, eine nur
in der älteren Historie vorhandene Archiv-Portnummer, zwei nicht vorhandene
Angaben (Administratorpasswort und zugesagter Produktivstart). Sollwerte werden
nicht an das Modell übergeben. M und V enthalten dieselben Daten, einschließlich
unveränderter Quellen/Metadaten. Keine echte Nutzerdatenbank wird verwendet.

3 Projekte × 3 Bedingungen × 5 Seeds = 45 unabhängige Generierungsaufrufe, jeweils
elf Antwortfelder. Seeds 3101–3105, Temperatur 0,7, num_ctx 8192, num_predict 512.
Modell `hf.co/google/gemma-4-12B-it-qat-q4_0-gguf:Q4_0`; Digest und Programm-/Harness-
Hashes werden gespeichert. Pro Projekt/Seed wird die Reihenfolge N/M/V mit festem
Zufallsstartwert 271828 permutiert. `keep_alive: 0` verhindert bewusst warm gehaltene
Modelle zwischen den Aufrufen; trotzdem keine verallgemeinerbare Latenzstudie.

Nur ein Versuch je Zelle, keine Reparatur, keine Wiederholung fehlgeschlagener Läufe.
Leeres/neues Ausgabeverzeichnis erforderlich. Fehler, Rohantworten, Ollama-Metriken,
Promptgröße in Zeichen und Laufzeit werden gespeichert. Der Selbsttest prüft vorab
Fixtureaufbau, Sollwertpräsenz, exakte Bewertung und Negativkontrollen ohne Modell.

## Bewertung und vorab festgelegte Pilotkriterien

JSON-Objekt mit elf vorgegebenen Schlüsseln und Stringwerten. Exakte Sollwerte,
keine positive Bewertung allein durch Auftreten eines Schlüsselwortes. `unbekannt`
ist nur bei den zwei tatsächlich unbeantwortbaren Fragen korrekt. Fehlende oder
ungültige Antworten zählen als falsch. Extra-/fehlende Felder werden als Formatfehler
berichtet. Falsche nichtleere Werte für unbekannte Angaben werden separat gezählt.

Für ein positives Ergebnis dieses engen Fortsetzungspiloten müssen alle gelten:

- V mindestens 135/165 Antworten richtig;
- V mindestens 29/30 unbekannte Angaben korrekt als `unbekannt`;
- V höchstens 5 richtige Antworten weniger als M (reine deskriptive Pilotgrenze,
  kein statistisch bewiesener Nichtunterlegenheitsnachweis);
- V mindestens 50 Prozentpunkte mehr richtige bekannte Fakten als N;
- keine technischen oder Formatfehler unter V.

Die Archiv-Portnummer fehlt absichtlich in M und V. Ihr echter Wert ist nur im
Bewertungsskript bekannt: `unbekannt` ist hier eine ehrliche Auslassung, aber kein
wiederhergestellter Fakt und zählt deshalb nicht als richtige Faktenantwort.
Zusätzlich separat berichten, wie häufig das Modell diese Kontextlücke ehrlich
benennt. Dieses erwartete Defizit zeigt die Grenze des gekürzten Snapshots; es darf
nicht nachträglich aus der Gesamtquote verschwinden. Die acht verfügbaren Fakten
werden für den Vergleich mit N getrennt ausgewertet.

Ergebnisse pro Frage, Projekt, Bedingung und Seed berichten, einschließlich aller Fehler.
Die Projekte teilen Struktur und mehrere Sollwerte; die wiederholten Läufe sind
keine repräsentative Stichprobe unabhängiger realer Projekte. Keine Signifikanz- oder
allgemeine Zuverlässigkeitsaussage aus zusammengezählten Antwortfeldern.

## Was das Ergebnis bedeutet

Ein Bestehen zeigt im synthetischen Fall funktionierende Kontextwiederherstellung
über den Testhost und faktentreue Fortsetzung mit dem getesteten Modell. Ein Vorteil
gegenüber N ist kein Beleg für besseres Denken oder Lernen und kein Beleg für einen
Vorteil gegenüber einer guten manuellen Übergabe. Ein negatives Ergebnis wird mit
unveränderten Kriterien veröffentlicht. Verbesserungen bekommen einen neuen Plan
und neue Daten statt nachträglicher Auswahl erfolgreicher Läufe.
