# Plan: R1 – Reparatur mit validierten Lehrerhinweisen, Gemma 4 12B

Abgestimmt zwischen Claude und Codex (Teamkanal #258–#276); gebaut von Claude, Prüfung und
Ausführung durch Codex. **Noch nicht eingefroren; keine Modellläufe.** Aufbau:
[`examples/r1/`](../../examples/r1/). **Pilot**: Die Schwellen sind
Pilotkriterien und bestätigen keinen spezifischen Effekt.

## Frage

Repariert 12B eine gescheiterte Erstlösung im ersten Reparaturversuch häufiger, wenn V-Mind
zur Fehlermeldung passende, validierte Lehrerhinweise liefert, als ohne Hinweis (O) und als mit
gleich langem fachfremdem Text (P)? Abruf und Nutzen werden getrennt gemessen.

## Fälle (vor jeder Reparatur festgeschrieben)

- Quelle: `docs/experiments/data/transfer-20261103` (Transfer-Pilot, Freeze 970d2dd), nur
  Bedingung **O** (im Erstprompt kein Hinweis), mindestens eine Prüfung nicht `ok`.
- **Bewertungsaufgaben** rezepte, termine, vorrat: 38 Fälle (14 / 15 / 9).
  **Lernaufgaben** ausgaben, leihliste: 29 Fälle (15 / 14); werden nie bewertet.
- Fehlerfamilie je Fall per fester Regel auf `abnahme.txt`, erste zutreffende gewinnt:
  1. `list_name`: `has no attribute 'list'`
  2. `ids_str`: `keine int` oder `IDs nach`
  3. `kaputte_datei`: `Corrupted|Damaged|JSONDecodeError|beschädigt`
  4. `kein_valueerror`: `ValueError not raised`
  5. `sonstige`
  Bestand Bewertung: list_name 19, ids_str 8, kaputte_datei 1, kein_valueerror 1, sonstige 9.
- Eindeutige Fallliste vor der Stichprobe: alle 38 Bewertungsfälle, sortiert nach
  (Aufgabe, Stufe, Ordnername) aufsteigend, Fall-Index 0–37 in dieser Reihenfolge.
- Auswahl 36 aus 38: Aus der in dieser Reihenfolge gefilterten Teilliste der Familie
  `list_name` streicht `random.Random(20261105).sample(teilliste, 2)` zwei Fälle; die übrigen
  36 behalten ihre Reihenfolge und werden neu von 0 bis 35 nummeriert.
- `faelle.json` vor allen Reparaturen: Fall-ID, Ordner, Aufgabe, ursprünglicher Seed, Familie,
  fehlgeschlagene Prüfungen, SHA-256 von `app.py` und `abnahme.txt`. Danach unverändert.

## Wissensbestand K (vor dem Freeze festgeschrieben)

Im Repository: `examples/r1/wissen/eintraege.json` (Texte und Nachweise),
`wissen/prompttexte.json` (ausgespielte Texte), `wissen/belege/` (vorher/nachher je Lernfall);
`r1_wissen.py` baut daraus eine neue Test-DB. 2 Lehrereinträge (list_name aus
haupt/015-leihliste-O-s1003, ids_str aus haupt/005-ausgaben-O-s1002, je mit Gegenprobe
vorher/nachher), 9 fachfremde Einträge aus den Rechner- und Routenplaner-Experimenten.

- Eigene Test-DB (installiertes vmind 0.2.0, Schema 5), Bereich `r1`.
- **Lehrereinträge** nur aus Lernfällen: je Familie mit mindestens einem Lernfall höchstens
  2 Einträge (`error_solution`). Familien ohne Lernfall (hier voraussichtlich `kaputte_datei`,
  `kein_valueerror`, `sonstige`) bekommen **keinen** Eintrag; Bewertungsfälle dieser Familien
  sind echte Abruflücken.
- Jeder Eintrag: `problem` beschreibt das Fehlerbild (inklusive Ausnahmetyp und Meldungstext,
  wie er in der Abnahme erscheint), `solution` nur das richtige Vorgehen. **Kein wörtliches
  falsches Codemuster** (Anlass: Routenplaner Seed 6004 schrieb ein zitiertes Fehlermuster ab).
  Kein Lösungscode einer Bewertungsaufgabe.
- Validierung nur durch tatsächlich ausgeführte Prüfung: Korrektur genau eines Lernfalls nach
  diesem Eintrag, danach bestehen die vorher fehlgeschlagenen Prüfungen dieses Falls; Nachweis
  mit Ordner und Ergebnis. Codex prüft die Einträge vor dem Freeze.
- **Fachfremde Einträge**: festgelegte Liste wahrer, validierter `error_solution` aus anderen
  Gebieten (z. B. Rechner- und Routenplanereinträge vom 4.11.), Bereich `global`. Sie dienen als
  realistische Ablenker für den Abruf und als Pool für P.

## Abfrage und Relevanzregel

- Anfrage: Ausnahmezeilen der Abnahme (Zeilen, die mit `AssertionError` oder `<Name>Error`
  beginnen), normalisiert (Zahlen -> `#`, Mehrfachleerzeichen zusammengefasst), dedupliziert,
  verbunden mit den Namen der fehlgeschlagenen Prüfungen; höchstens 400 Zeichen.
- Abruf: JSONL `recall` (vmind 0.2.0) mit `scope: r1`, `limit: 10`.
- Ein Treffer ist **passend**, wenn er validiert ist, `kind = error_solution` hat und sein
  `problem` mindestens eine Bedingung erfüllt:
  a) Ausnahmetyp der Anfrage **und** ein Bezeichner aus derselben Meldung (Wörter in
     Anführungszeichen oder nach `attribute`), jeweils als ganzes Token; oder
  b) eine Assertion-Meldung der Anfrage exakt als normalisierter Teiltext.
- Höchstens 3 passende Treffer in Rangfolge. Keiner passend: Gedächtnis leer. Für Familien
  ohne Lehrereintrag heißt das „kein passender Eintrag“; der rohe Abruf kann trotzdem Treffer
  liefern, die die Regel verwirft oder fälschlich annimmt (dann Abruf „falsch“).
- Prompt-Format je Hinweis: `{"wann": …, "richtig": …}` aus der festgeschriebenen Datei
  `examples/r1/wissen/prompttexte.json`, für **jeden** ausgespielten Treffer gleich, in L (auch
  fachfremde Fehlabrufe) und in P. Nie der DB-Rohtext; Quelle, Nachweis und Belege nicht im
  Prompt. Prompttexte enthalten kein falsches Codemuster.
- **Gemeinsame Längengrenze für L und P:** `wann` höchstens 300 Zeichen, `richtig` höchstens
  600 Zeichen (jeweils hart abgeschnitten), also höchstens 900 Zeichen je Hinweis und 2700
  Zeichen je Gedächtnis. P-Einträge werden nach derselben Regel gekürzt.

## Arme (je Fall alle drei, gleicher Seed)

| Arm | Gedächtnis |
|---|---|
| O | leer |
| L | passende Treffer nach Relevanzregel (0–3) |
| P | nur wenn L nicht leer: gleich viele fachfremde Einträge aus dem Pool, je Eintrag der mit der nächsten Länge zur jeweiligen L-Länge (Gleichstand: kleinere ID); sonst leer |

- Reparaturprompt in allen Armen gleich bis auf das Gedächtnis: Aufgabentext wie im Pilot,
  bisheriger Code, Abnahmeausgabe gekürzt (Namen der fehlgeschlagenen Prüfungen plus
  Ausnahmezeilen, höchstens 1500 Zeichen), Bitte um die vollständige korrigierte `app.py`.
- System wie im Pilot, Modell und Digest wie im Pilot, Temperatur 0,7, `num_predict` wie im
  Pilot. Seed je Fall `7000 + Fall-Index`, in allen Armen gleich.
- Reihenfolge der 108 Aufrufe per `random.Random(20261106)` gemischt.

## Abrufgüte (getrennt, nicht Kriterium)

Je Fall: **richtig** (mindestens ein passender Treffer gehört zur Familie des Falls),
**falsch** (nicht leer, aber keiner der Familie), **leer**. Bericht je Familie und Aufgabe.

## Messgrößen

- **Haupt:** Reparatur erfolgreich = nach dem Reparaturversuch bestehen alle Prüfungen der
  Abnahme.
- Neben: vorher fehlgeschlagene Prüfungen behoben; **Regression** = eine vorher bestandene
  Prüfung scheitert danach; neue Fehlerarten; Zeit und Tokens je Lauf und je erfolgreicher
  Reparatur.
- **Technischer Ausfall:** HTTP-Fehler, Zeitüberschreitung, `done_reason != stop`, leere
  Antwort. Zählt als nicht repariert. Läuft die Abnahme nicht durch, ist die Regression des
  Falls **unbekannt** und wird getrennt berichtet.

## Kriterien (vorläufig, Pilot)

1. L − O ≥ 15 pp beim Hauptmaß.
2. McNemar L gegen O, einseitig exakt, p < 0,05.
3. L − P ≥ 10 pp.
4. Regressionsanteil L − O ≤ 10 pp. **Fester Nenner:** immer 36 Fälle je Arm. Hauptrechnung:
   Fälle mit unbekannter Regression (Abnahme nicht durchgelaufen) zählen als ohne Regression,
   ihre Zahl wird je Arm berichtet. Sensitivität: unbekannt unter L als Regression, unter O und
   P nicht; das Kriterium muss in beiden Rechnungen erfüllt sein.
5. Ungültig ohne Ergebnis: mehr als 10 % der 108 Aufrufe technisch ausgefallen (≥ 11),
   fehlende oder doppelte Läufe.

Zusätzlich beschreibend: L − P nur über Fälle mit nicht leerem Gedächtnis.

## Simulation (bedingt auf Annahmen)

`examples/r1/r1_trennschaerfe.py`, 4000 Läufe je Szenario. Annahmen: O-Reparaturrate 30 %,
Abruf richtig 80 %, falsch 10 %, Regression 10 %. N = 36: kein Effekt 0,01; nur unspezifisch
+10 pp 0,05, +20 pp **0,12**; Effekt 20 / 30 / 40 pp 0,29 / 0,56 / 0,78; 30 pp mit Regression
+25 pp 0,05. Der Fehlalarm bei starkem unspezifischem Effekt ist wesentlich; ein positives
Ergebnis heißt daher nur „im Pilot über den Schwellen“.

## Budget und Host-Schutz

Exakt 108 Generierungen (36 × 3) einschließlich Fehlanfragen; vor dem Senden protokolliert;
kein Lauf wiederholt, kein Nachfüllen; unvollständiger Laufordner stoppt den Host. Läufe nur am
eingefrorenen Commit. Bau und Ausführung durch Codex (Schreibrecht im Repository).

## Grenzen

- Drei Aufgaben aus demselben Pilot, gleiche Fehlerfamilien; Ergebnis gilt nur dafür.
- Familien ohne Lernfall bekommen keinen Hinweis; L kann dort nicht besser sein.
- Einträge schreibt Claude nach Sichtung der Lernfälle; die Relevanzregel ist auf deren
  Wortlaut abgestimmt. Abrufgüte daher getrennt berichten.
- Generierter Code läuft ohne Sandbox wie im Pilot.

## Umsetzung

`examples/r1/`: `r1_werkzeuge.py` (Fallauswahl, Familie, Anfrage, Relevanzregel, P-Zuteilung,
Prompt, Zeitplan), `r1_wissen.py` (baut K als neue Test-DB), `r1_host.py` (Vorbereitung
`faelle.json`, `wissen.db`, `abruf.json` ohne Modell, dann die Läufe), `r1_auswerten.py`
(Kriterien, Gültigkeit, Aufschlüsselung), `test_r1.py`, `selbsttest.py`, `r1_trennschaerfe.py`.
Aufgabentexte, Systemprompt, Modellprüfung, Abnahme und Referenzlösungen kommen unverändert aus
`examples/transfer` (Transfer-Pilot). Abruf über JSONL `recall` des installierten vmind mit
`limit` 10, damit R1 nicht von der noch nicht integrierten CLI-Option `--limit` abhängt.

**Offen vor dem Freeze bekannt:** Die Vorbereitung (auch in der Attrappe) berechnet den Abruf für
die Bewertungsfälle deterministisch und ohne Modell. Ergebnis des Attrappenlaufs: Familie
list_name 17/17 und ids_str 8/8 mit richtigem Lehrereintrag, die 11 Fälle der Familien ohne
Lehrereintrag ohne passenden Eintrag, kein falscher Treffer. Relevanzregel und Einträge wurden
danach nicht verändert. Die Reparaturwirkung ist damit nicht bekannt.
