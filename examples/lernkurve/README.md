# Lernkurve: lernt ein kleines Modell aus eigenen, geprüften Fehlern?

Versuchsplan, Hypothesen und vorab festgelegtes Erfolgskriterium:
[docs/experiments/lernkurve-plan.md](../../docs/experiments/lernkurve-plan.md).

| Datei | Inhalt |
|---|---|
| `aufgaben/*/spec.md` | Aufgabenbeschreibung, die das Modell erhält |
| `aufgaben/*/abnahme.py` | unabhängige Abnahme je Aufgabe (2 spezifische Prüfungen) |
| `aufgaben/gemeinsam.py` | 7 gemeinsame Fallstrick-Prüfungen für alle Aufgaben |
| `referenz/` | korrekte Lösungen, **nur** für den Selbsttest, nie im Modellkontext |
| `selbsttest.py` | prüft die Abnahmen: Referenzen bestehen alles, eingebaute Fehler werden erkannt |
| `run.py` | Testhost mit den Bedingungen A, B und C |
| `auswerten.py` | Tabellen nach Bedingung und Position |

Voraussetzungen: installiertes `vmind` (mit Prüfbefehlen, Schema 4), Ollama mit dem Modell
`vmind-gemma4:e2b` (siehe `setup/Modelfile`), Python 3. Generierter Code läuft ohne
Isolation mit den Rechten des Nutzers; nur auf einem eigenen Rechner ausführen.

Selbsttest der Abnahmen, ohne Modell:

```sh
python3 examples/lernkurve/selbsttest.py
```

Probelauf mit zwei Aufgaben:

```sh
python3 examples/lernkurve/run.py --ausgabe ../v-mind-lernkurve/probe --aufgaben aufgabenplaner,kontakte --feste-reihenfolge --seeds 42
```

Hauptlauf nach Plan (3 Reihenfolgen × 2 Seeds × 3 Bedingungen, mehrere Stunden):

```sh
python3 examples/lernkurve/run.py --ausgabe ../v-mind-lernkurve/hauptlauf
```

Auswertung:

```sh
python3 examples/lernkurve/auswerten.py ../v-mind-lernkurve/hauptlauf
```

Jeder Durchgang erhält einen eigenen Ordner mit eigener V-Mind-Datenbank, allen Prompts,
Modellantworten, Abnahmeausgaben und `ergebnis.json`. Diese Daten gehören nicht ins
Repository.
