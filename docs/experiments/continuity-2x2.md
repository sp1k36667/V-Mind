# Fortsetzungs-Folgelauf 2×2: weniger veraltete Werte, kein allgemeiner Genauigkeitsgewinn

Ausgeführt am 1. November 2026. Eingefrorener Plan/Harness:
`83114c692ce16e0c976a40a7054d17c1bcdcc23c`.
[Vorabplan](continuity-2x2-plan.md), [Rohdaten aller 80 Aufrufe](data/continuity-2x2-20261101/results.jsonl),
[Metadaten und Prüfsummen](data/continuity-2x2-20261101/metadata.json),
[unveränderte Abnahmeauswertung](data/continuity-2x2-20261101/summary.json).

## Aufbau

Vier neue synthetische Projekte, fünf neue Seeds, vier Bedingungen. J0/T0 verwenden
`resume` vor der Filterkorrektur, Ja/Ta nach der Korrektur. J steht für JSON,
T für eine verlustfreie flache Feldliste desselben Snapshots. Beide Release-Binaries
und ihre Prüfsummen wurden vor dem Lauf unabhängig kontrolliert; der Selbsttest für
Fixtures, Fenster, identische Kontrollprompts und Abnahmeregeln bestand.
Kein Versuch wurde ersetzt, repariert oder erneut ausgeführt.

Anders als im ersten 45er-Pilot erzwingt der Host ein JSON-Ausgabeschema mit allen elf
Fragefeldern. Es enthält keine Antwortvorgaben. **Die Ergebnisse sind deshalb kein
Vorher-nachher-Vergleich mit dem ersten Pilot.** Modell und Host laden weiterhin nur
Snapshots; kein MCP-Werkzeuggebrauch und kein Training.

## Unveränderte Ergebnisse und Abnahme

Je Bedingung 20 Aufrufe. Acht verfügbare Fakten ergeben 160 Bewertungen, zwei wirklich
unbekannte Angaben 40 weitere. Die zusätzliche Archiv-Portfrage liegt absichtlich
außerhalb beider Snapshotfenster und wird separat ausgewiesen.

| Messgröße | J0 | T0 | Ja | Ta |
|---|---:|---:|---:|---:|
| Verfügbare Fakten richtig (von 160) | 159 | 152 | 156 | 144 |
| Unbekannte Angaben richtig als unbekannt (von 40) | 40 | 40 | 40 | 40 |
| Richtige Antworten insgesamt (von 220) | 199 | 192 | 196 | 184 |
| Überholter nächster Schritt, Projekte 0–2 (von 15) | 1 | 2 | 0 | 0 |
| Technische/Formatfehler | 0 | 0 | 0 | 0 |
| Erfundene Werte bei den unbekannten Angaben | 0 | 0 | 0 | 0 |
| Nicht enthaltene Archiv-Portnummer als unbekannt (von 20) | 20 | 20 | 20 | 20 |

Strenge und vorab festgelegte milde Bewertung liefern hier dieselben Punktzahlen.
`acceptance.passed` ist **true**: Die absoluten Untergrenzen für Ja/Ta sind erreicht,
beide Formate nennen weniger alte nächste Schritte, und Ja liegt nicht unter Ta.
Ta liegt mit 144/160 genau auf seiner Mindestgrenze. Das ist eine **lokale deskriptive
Abnahme**, kein statistischer Gleichwertigkeits- oder allgemeiner Nutzennachweis.

**Die Gesamtgenauigkeit steigt nicht:** Nach dem Filter liegen JSON bei 156 statt
159 und Text bei 144 statt 152 richtigen verfügbaren Fakten. Deshalb darf das
Bestehen nicht als „12B wurde insgesamt besser“ oder als allgemeine Lernwirkung
beworben werden. Der enge positive Befund ist die Abnahme alter next_step-Werte von
insgesamt drei auf null in den hierfür vorgesehenen alten/neuen Bedingungen.

## Ergebnisse je Frage

Je Frage und Spalte 20 Antworten:

| Frage | J0 | T0 | Ja | Ta |
|---|---:|---:|---:|---:|
| release | 20 | 20 | 20 | 20 |
| folder | 20 | 20 | 20 | 20 |
| backend | 20 | 19 | 19 | 18 |
| schema | 20 | 20 | 20 | 20 |
| search | 20 | 20 | 20 | 20 |
| next | 19 | 13 | 17 | 6 |
| assistant | 20 | 20 | 20 | 20 |
| gpu | 20 | 20 | 20 | 20 |
| archive_port | 0 | 0 | 0 | 0 |
| password | 20 | 20 | 20 | 20 |
| production_date | 20 | 20 | 20 | 20 |


## Nachträgliche beschreibende Fehleranalyse: Nummer statt Text

Claude und Codex haben Rohdaten und Summen unabhängig gegengeprüft. Die folgenden
Kategorien wurden nach dem Lauf analysiert; sie ändern die vorab festgelegte
Bewertung nicht.

| Antwort auf die Frage nach dem nächsten Schritt | J0 | T0 | Ja | Ta |
|---|---:|---:|---:|---:|
| Erwarteter Text | 19 | 13 | 17 | 6 |
| Bekannter überholter Text | 1 | 2 | 0 | 0 |
| ID des aktuellen next_step-Datensatzes | 0 | 5 | 3 | 14 |

Alle nicht überholten falschen next-Antworten sind tatsächlich die Nummer des
aktuellen Datensatzes, zum Beispiel `22` statt `kran-abnahme`. Die Frage lautete
„nur die Kennung“. Eine ID ist eine vertretbare Lesart dieser mehrdeutigen Formulierung.
Das ist eine wichtige Messgrenze: Diese Antworten sind nach dem eingefrorenen
Sollwert falsch, aber kein Beleg dafür, dass das Modell einen anderen Arbeitsauftrag
für aktuell hält. Die übrigen Punktverluste betreffen zusätzliche Wörter beim Backend,
zum Beispiel „Backend SQLite“ statt des exakten Sollwerts „SQLite“.

Der Effekt tritt auch in der Kontrolle auf: Dort sind vollständige Snapshots,
Prompt-Hashes und bei gleichem Seed sogar rohe Antworttexte vor/nach dem Filter
identisch. T0 und Ta antworten im Kontrollprojekt jeweils fünfmal mit `17`.
Das spricht gegen einen allgemeinen Genauigkeitsgewinn durch die Filteränderung
und zeigt das Zusammenspiel von Darstellung und Frageformulierung.

## Produktfolgen und Grenzen

- Überholte Zustandsereignisse gehören nicht als konkurrierende aktuelle Angaben in
  einen Startsnapshot. Die Korrektur erhält die vollständige Historie im journal.
- JSON war in diesem Aufbau genauer als die flache Liste; der erste Pilot zeigte die
  umgekehrte Richtung. Ein allgemeines „Text ist besser“ folgt aus keinem der Läufe.
- Für eine genaue Abfrage sollte ausdrücklich nach dem Text eines Schritts statt
  mehrdeutig nach seiner Kennung gefragt werden. Hier wird die Formulierung nicht
  nachträglich korrigiert oder erneut gezählt.
- Ausgabeformate vom Host zu prüfen verhindert zusätzliche/fehlende Felder in diesem
  Aufbau; es beweist keine fachliche Richtigkeit der erzeugten Werte.
- Vier ähnlich aufgebaute Projekte und fünf Seeds sind keine repräsentative Stichprobe
  echter Entwicklungsprojekte. Keine neue Transfer- oder Lernbehauptung, keine p-Wert-
  Interpretation aus geklumpten Antwortfeldern. Ein weiterer Lauf braucht einen neuen Plan.

Alle API-Antworten und gemessenen Laufzeiten stehen in den Rohdaten. Der reine
SQLite-Betrieb und die automatische Host-Protokollierung wurden durch diesen
Modellversuch nicht abgenommen; dafür gibt es getrennte Integrationstests.
