# Transfer-Pilot mit Gemma 4 12B: Ergebnis

**Vorab festgelegtes Ergebnis: nicht bestanden.** Das Erfolgskriterium des Hauptlaufs
wurde verfehlt, und die Schadensgrenze des Gegenfalls ist formal verletzt. Alle drei
Stufen sind gültig: 170 von 170 geplanten Läufen, keine technischen Ausfälle.

Plan: [transfer-pilot-plan.md](transfer-pilot-plan.md), eingefroren in Commit
`970d2ddc092159c5c48466aaf6de5cc9afd4b8b9`. Host und Aufgaben:
[`examples/transfer/`](../../examples/transfer/). Daten:
[`data/transfer-20261103/`](data/transfer-20261103/).

## Frage

Hilft eine einzelne, korrekte Erfahrung im Prompt Gemma 4 12B bei neuen Aufgaben, einen
bestimmten Fehler zu vermeiden (JSON-Objektschlüssel sind nach dem Laden Strings; numerische
ID-Schlüssel müssen umgewandelt werden), ohne dort zu schaden, wo die Regel nicht gilt?
Verglichen wurden O (keine Erfahrung), L (die Erfahrung) und P (gleich langes, wahres,
themenfernes Placebo), je im ersten Versuch.

## Durchführung

- Modell `hf.co/google/gemma-4-12B-it-qat-q4_0-gguf:Q4_0`, Digest `18a4d951…6acd`,
  Temperatur 0,7; vom Host vor jeder Stufe geprüft. Läufe am 2. und 3. November 2026
  (etwa 25–28 s je Lauf), ausgeführt von Codex aus einem separaten Checkout des
  Freeze-Commits, nur eine Host-Instanz, keine anderen Modelle geladen.
- Vorlauf (O, 20 Läufe) vor dem Hauptlauf; Hauptlauf (120 Läufe, 40 gepaarte Aufgabe/Seed)
  und Gegenfall (30 Läufe) danach. Kein Lauf wurde wiederholt, nichts an Aufgaben, Texten,
  Seeds oder Schwellen nach den Daten geändert.
- Auswertung mit dem eingefrorenen `auswerten.py`. Claude hat sie aus `git archive 970d2dd`
  unabhängig wiederholt und die Zahlen zusätzlich direkt aus den Ergebnisdateien gezählt;
  Codex hat sie ebenfalls bestätigt.

## Vorab festgelegte Auswertung

**Vorlauf** (Gate): Zielprüfung 1 von 20 bestanden (5 %, Grenze höchstens 12). Gültig,
Fortsetzung zulässig.

**Hauptlauf**, Zielprüfung im ersten Versuch:

| Bedingung | bestanden | Anteil |
|---|---:|---:|
| O, keine Erfahrung | 2 / 40 | 5 % |
| L, Erfahrung | 13 / 40 | 32,5 % |
| P, Placebo | 10 / 40 | 25 % |

| Kriterium | gefordert | Ergebnis | |
|---|---|---|---|
| L über O | ≥ 30 pp | 27,5 pp | verfehlt |
| McNemar L gegen O, einseitig exakt | p < 0,05 | b/c = 12/1, p = 0,0017 | erfüllt |
| L über P | ≥ 20 pp | 7,5 pp | verfehlt |
| Aufgaben mit L > O | ≥ 3 von 4 | 4 von 4 | erfüllt |
| Schaden übrige Prüfungen (L gegen O) | ≤ 10 pp | 7,1 pp (O 75,0 %, L 67,9 %, P 76,4 %) | eingehalten |

Je Aufgabe (bestanden O / L / P von je 10): `ausgaben` 0 / 4 / 3, `leihliste` 1 / 2 / 2,
`rezepte` 1 / 4 / 1, `termine` 0 / 3 / 4.

**Gegenfall** (`vorrat`, Namensschlüssel), Zielprüfung bestanden: O 3 / 10, L 1 / 10,
P 1 / 10. Fehlschläge unter L 9 gegenüber 7 unter O, also 2 mehr; erlaubt war höchstens 1.
Schadensgrenze verletzt. Übrige Prüfungen in allen Bedingungen 37 / 50.

**Gesamtergebnis:** nicht bestanden (Erfolgskriterium verfehlt; Schadensgrenze des
Gegenfalls verletzt).

## Nachträgliche Beschreibung (nicht vorab geplant)

Die folgenden Zahlen erklären das Ergebnis, ändern es aber nicht. Sie stammen aus
[`ursachen.py`](data/transfer-20261103/ursachen.py): je Fehlschlag die erste Fehlerzeile
der Zielprüfung, zu Klassen zusammengefasst.

| Ursache des Fehlschlags (Hauptlauf) | O | L | P |
|---|---:|---:|---:|
| Methode `list` fehlt (z. B. `list_items`) | 22 | 18 | 16 |
| IDs nach dem Neuladen keine `int` | 13 | 0 | 10 |
| ID nach dem Neuladen nicht gefunden | 2 | 5 | 2 |
| Umwandlung auf falschem Typ (`isdigit` auf `int`) | 0 | 2 | 0 |
| sonstige (beschädigte Datei, Syntaxfehler, Typvergleich, leere Liste) | 1 | 2 | 2 |
| bestanden | 2 | 13 | 10 |

Beobachtungen:

1. **Der häufigste Fehlschlag hat mit der Erfahrung nichts zu tun.** In 56 von 120
   Hauptläufen (und in 24 von 30 Gegenproben) heißt die verlangte Methode `list()`
   anders, meist `list_items`, vermutlich um den eingebauten Namen nicht zu überdecken.
   Die Zielprüfung bricht dann ab, **bevor** sie den ID-Typ prüft: In diesen Läufen war
   der gemessene Fehler gar nicht beobachtbar. Das begrenzt, was L überhaupt verbessern
   konnte.
2. **Der gezielte Fehler „IDs nach dem Neuladen keine int“ tritt unter L nicht mehr auf**
   (O 13, L 0, P 10). Unter L kommen dafür andere ID-Fehler vor (5-mal „nicht gefunden“,
   2-mal falsch angewandte Umwandlung). Unter den Läufen, in denen `list` vorhanden war,
   bestanden O 2 von 18, L 13 von 22 und P 10 von 24. Das ist **kein fairer Vergleich**:
   Ob `list` vorhanden ist, kann selbst von der Bedingung abhängen, und die Gruppen sind
   klein.
3. **Ein Teil des Anstiegs ist unspezifisch.** Auch das Placebo hebt die Zielquote von
   5 % auf 25 %. Schon ein gefülltes Feld `gedaechtnis` scheint die Antworten zu
   verändern; hier unterscheiden sich L und P nur um 7,5 pp.
4. **Der Gegenfall sagt über Schäden durch die Erfahrung fast nichts.** Unter L fehlte
   `list` in 9 von 10 Gegenproben, unter P ebenso, unter O in 6 von 10 (dazu ein
   Dateifehler). Keine einzige Gegenprobe scheiterte daran, dass Namensschlüssel in Zahlen
   umgewandelt wurden. Die formale Grenzverletzung entsteht also aus dem Benennungsfehler;
   ob die Erfahrung im Gegenfall schadet, ist mit einer einzigen beobachtbaren L-Probe
   nicht zu beurteilen. Die vorab festgelegte Grenze bleibt trotzdem verletzt.

Grenzen dieser Beschreibung: Sie nutzt nur die erste Fehlerzeile; nach dem ersten Fehler
können weitere unentdeckt bleiben. Die Klassen wurden nach Sicht der Daten gebildet.

## Was das Ergebnis bedeutet

- **Belegt (vorab festgelegt):** Mit dieser Aufgabenfassung, diesem Prompt und 12B
  erreicht die Erfahrung nicht den geforderten Abstand zu O und nicht zum Placebo. Das ist
  ein Negativergebnis für diesen Versuchsaufbau.
- **Beschrieben, nicht belegt:** Die Erfahrung scheint genau den Fehler zu verhindern, auf
  den sie zielt, wo er beobachtbar war. Ein Aufgabenfehler ohne Bezug zur Erfahrung
  überdeckt das, und ein unspezifischer Prompteffekt erklärt einen Teil der Verbesserung.
- **Nicht gezeigt:** dass V-Mind-Erfahrungen allgemein beim Lernen helfen, dass sie
  allgemein schaden, oder wie sich eine selbst erworbene Erfahrung verhält. Die geplante
  Stufe „Erwerb“ entfällt, weil schon die von Hand geschriebene Erfahrung das Kriterium
  verfehlt.

## Mögliche Folgefragen (nicht durchgeführt)

Nur als neuer, vorab eingefrorener Plan mit neuen Seeds; nichts davon wird auf diesen
Daten nachgebessert:

- Die Pflicht zur Methode `list()` so prüfen, dass ein Benennungsfehler die Messung nicht
  verdeckt, etwa als getrennte Vorbedingung, die ausgewiesen statt mitgezählt wird.
- Den unspezifischen Effekt eines gefüllten Gedächtnisfelds eigens messen (leeres Feld,
  Placebo, passende Erfahrung, mehrere Placebos).
- Einen Gegenfall wählen, in dem die Fehlanwendung tatsächlich beobachtbar ist.

## Daten und Nachrechnung

[`data/transfer-20261103/`](data/transfer-20261103/) enthält je Stufe `einstellungen.json`
und je Lauf `app.py`, `abnahme.txt` und `ergebnis.json`, mit Platzhaltern statt lokaler
Pfade. Nicht enthalten sind die vollständigen Modellanfragen und -antworten
(`generierung.json`); sie liegen lokal beim Nutzer. `auswertung-970d2dd.json` ist die
Ausgabe des eingefrorenen `auswerten.py`, `ursachen.json` die der nachträglichen Analyse.

Nachrechnen der Ursachen (im Repository):

```sh
python3 docs/experiments/data/transfer-20261103/ursachen.py
```

Die vorab festgelegte Auswertung prüft die Läufe gegen den Zeitplan und den Plan-Hash und
läuft deshalb auf den originalen Laufordnern am Freeze-Commit:

```sh
python3 examples/transfer/auswerten.py VORLAUF HAUPT GEGENFALL
```

Review: Durchführung Codex; unabhängige Nachrechnung Claude (Teamkanal #174, #177, #178);
Bestätigung Codex (#176, #179).
