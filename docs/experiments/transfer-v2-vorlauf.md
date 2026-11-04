# Transfer v2 mit Gemma 4 12B: Vorlauf, kein Hauptvergleich

**Vorab festgelegtes Ergebnis: v2 endet ohne Ergebnis.** Der Vorlauf ist gültig
(208 von 208 geplanten Läufen, keine technischen Ausfälle), aber zu wenige Kandidaten
erfüllen die Vorlaufregeln: Gruppe A hat 2, Gruppe B 1 eingeschlossene Aufgabe, nötig
sind je mindestens 3. Nach Plan finden Hauptlauf und Gegenfälle nicht statt. Über die
Frage, ob gekreuzte Erfahrungen gezielt helfen, sagt dieser Lauf daher nichts.

Plan: [transfer-v2-plan.md](transfer-v2-plan.md), eingefroren in Commit
`5895f0ca57d076dc59c0f4b1386fe6c229187b72`. Host und Aufgaben:
[`examples/transfer-v2/`](../../examples/transfer-v2/). Daten:
[`data/transfer-v2-20261104/`](data/transfer-v2-20261104/).

## Frage des Vorlaufs

Der Vorlauf wählt vor dem Hauptvergleich aus je 6 Kandidaten der Gruppen A
(JSON-Schlüssel nach dem Laden sind Strings) und B (`isinstance(True, int)` ist wahr) die
Aufgaben aus, die für 12B im messbaren Bereich liegen: mit direktem Hinweis lösbar, ohne
Hinweis aber nicht schon meistens richtig. Er prüft außerdem, ob die beiden Gegenfälle
ohne Hinweis lösbar sind.

## Durchführung

- Modell wie im Pilot (Gemma 4 12B, Q4_0, Digest vom Host geprüft), Temperatur 0,7.
  Bedingungen O (kein Hinweis) und D (direkter Hinweis), je 8 Seeds (2001–2008);
  Gegenfälle nur O.
- **Erster Durchgang, nicht gewertet:** Am 3. November 2026 lief der Vorlauf am selben
  Freeze auf `/run/media/sp1k3/Code2`. Ein Stromausfall unterbrach ihn nach 171
  gespeicherten Ergebnissen (letztes um 20:48). Dieser Durchgang ist unvollständig und
  wird nicht ausgewertet; seine Ergebnisse wurden für diesen Bericht nicht gelesen.
- **Gewerteter Durchgang:** Codex startete den Vorlauf am 4. November 2026 neu, am
  sauberen Freeze-Commit, in einem neuen Ausgabeordner auf einem ext4-Dateisystem,
  eine Host-Instanz. Läufe etwa 14:36 bis 15:37 Uhr. Kein Lauf wurde wiederholt oder
  ausgelassen, nichts an Aufgaben, Texten, Seeds oder Schwellen nach den Daten geändert.
- Auswertung mit dem eingefrorenen `auswerten.py`. Claude hat sie aus
  `git archive 5895f0c` unabhängig wiederholt und die Zielstatus zusätzlich direkt aus
  allen `ergebnis.json` gezählt; beides stimmt in jeder Aufgabe und Bedingung überein.
  Codex hat dieselben Zahlen bestätigt. Die abgelegte Auswertung
  ([`auswertung-5895f0c.json`](data/transfer-v2-20261104/auswertung-5895f0c.json)) ist
  über die Kopie im Repository erzeugt.

## Vorab festgelegte Auswertung

Gates je Kandidat (Nenner immer 8 geplante Läufe): G1 D-Zielprüfung ≥ 6/8, G2
O-Zielprüfung ≤ 4/8, G3 übrige O-Prüfungen ≥ 80 %, G4 Gegenfall O ≥ 6/8. Eingeschlossen
ist ein Kandidat mit G1–G3; je Gruppe sind mindestens 3 nötig.

Zielprüfung bestanden (von 8), in der festgelegten Reihenfolge:

| Gruppe | Kandidat | O | D | G1 | G2 | G3 | eingeschlossen |
|---|---|---:|---:|:-:|:-:|:-:|:-:|
| A | zitate | 8 | 8 | ja | nein | ja | nein |
| A | geschenkideen | 4 | 8 | ja | ja | ja | **ja** |
| A | vokabeln | 6 | 8 | ja | nein | ja | nein |
| A | filmliste | 7 | 7 ¹ | ja | nein | ja | nein |
| A | rezeptideen | 4 ¹ | 8 | ja | ja | ja | **ja** |
| A | reiseziele | 8 | 8 | ja | nein | ja | nein |
| B | trainingslog | 7 | 8 | ja | nein | ja | nein |
| B | punktestand | 8 | 8 | ja | nein | ja | nein |
| B | pflanzen | 3 | 8 | ja | ja | ja | **ja** |
| B | budget | 6 | 8 | ja | nein | ja | nein |
| B | lesezeit | 8 | 8 | ja | nein | ja | nein |
| B | wasserzaehler | 8 | 8 | ja | nein | ja | nein |

¹ Je ein Lauf „nicht beobachtbar“ (Vorbedingung der Zielprüfung nicht erreicht), zählt
nicht als bestanden.

| Prüfung | Ergebnis | |
|---|---|---|
| Gültigkeit | 208/208, technisch 0, Abbruch 0 | erfüllt |
| G1 lösbar mit Hinweis | 12 von 12 Kandidaten | erfüllt |
| G2 Spielraum ohne Hinweis | 3 von 12 Kandidaten | überwiegend verfehlt |
| G3 übrige Prüfungen | 12 von 12 (O 478/480, D 479/480) | erfüllt |
| G4 Gegenfälle prüfbar | postleitzahlen 8/8, gewohnheiten 8/8 | erfüllt |
| Gruppe A auswertbar (≥ 3) | 2 | **verfehlt** |
| Gruppe B auswertbar (≥ 3) | 1 | **verfehlt** |

Damit gilt laut Plan: v2 endet ohne Ergebnis, keine Wiederholung; eine neue Planfassung
mit neuen Kandidaten und Seeds wäre nötig.

## Beschreibende Befunde (nachträglich, kein Kriterium)

- **Die Aufgaben sind für 12B überwiegend zu leicht.** Ohne Hinweis bestand O die
  Zielprüfung in 77 von 96 Kandidatenläufen (80 %; 18 verfehlt, 1 nicht beobachtbar),
  in den Gegenfällen 16 von 16. 5 Kandidaten lagen bei 8/8, 4 weitere
  bei 6–7/8. Der Plan nahm für O eine Grundrate um 30 % an; das Simulationsszenario mit
  Grundrate 50 % ergab schon nur 0,18 Gesamterfolg, mit dem Hauptgrund „Gruppe nicht
  auswertbar“. Genau dieser Fall ist eingetreten.
- **Die Fallen sind spezifisch.** Alle 18 verfehlten O-Läufe scheitern an der
  Zielprüfung; die übrigen Prüfungen bestehen dort bis auf einen Lauf (zusätzlich ein
  Fehler im Neuladetest). Wo 12B in die Falle tritt, misst die Prüfung also das Richtige. Er tritt
  nur selten hinein.
- **Mit Hinweis ist fast alles lösbar:** D bestand 95 von 96 Läufen, einer war nicht
  beobachtbar. Die Machbarkeit (G1) war kein Engpass.
- **Gegenüber dem Pilot ist die Schwierigkeit gekippt.** Im Pilot bestand O die
  Zielprüfung im Vorlauf 1 von 20 (5 %), hier 77 von 96 (80 %). Die Aufgaben unterscheiden
  sich (v2 gibt ein Gerüst vor, Fallen und Spezifikationen sind anders); welcher
  Unterschied den Ausschlag gibt, zeigt dieser Lauf nicht. Plausibel, aber nicht
  geprüft: Das Gerüst nimmt dem Modell einen Teil der Fehlerquellen ab.

## Folgerung

Die Vorlaufregel hat getan, wofür sie gedacht war: Statt einen Hauptvergleich auf
Aufgaben zu stützen, bei denen O fast immer besteht und kein Effekt messbar wäre, endet
v2 ohne Ergebnis. Ein weiterer Versuch braucht Aufgaben mit einer Schwierigkeit zwischen
Pilot und v2, wieder vorab mit eigenen Kandidaten, Seeds und Kriterien festgelegt. Ein
Nachschieben von Kandidaten oder eine gelockerte Schwelle für diesen Lauf wäre eine
Anpassung nach den Daten und ist ausgeschlossen.

## Grenzen

- Nur Vorlauf: keine Aussage über den Nutzen von Erfahrungen, keine über Schaden.
- Je Kandidat 8 Läufe; einzelne G2-Entscheidungen nahe der Schwelle (4/8, 6/8) sind
  zufallsabhängig. Das ändert die Gesamtaussage nicht: Selbst wenn die nächsten Fälle
  mit 6/8 (vokabeln, budget) zählten, hätte Gruppe B nur 2 Aufgaben. Die Regel ist
  ohnehin fest.
- Die nachträglichen Befunde sind beschreibend und nicht vorab geplant.
- Generierter Code lief ohne Sandbox wie im Pilot.
