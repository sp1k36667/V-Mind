# Plan: Transfer v2 mit Gemma 4 12B (gekreuzte Erfahrungen)

**Status: Entwurf zur Prüfung durch Codex. Nicht eingefroren, nichts gebaut, kein
Modelllauf.** Grundlage: Ergebnis und Grenzen des ersten Pilots
([transfer-pilot.md](transfer-pilot.md)) und die Abstimmung im Teamkanal (#182–#188).
Zahlen in eckigen Klammern legt erst das Baupaket fest; sie werden vor dem Freeze
eingetragen und ändern keine Regel dieses Plans.

## Frage

Verhindert eine passende Erfahrung im Prompt bei Gemma 4 12B gezielt den Fehler, auf
den sie sich bezieht, und zwar deutlich besser als eine unpassende Erfahrung gleicher
Art? Und schadet sie dort, wo die Regel nicht gilt?

Der erste Pilot konnte das nicht trennen: Ein Benennungsfehler ohne Bezug zur Erfahrung
verdeckte die Messung, und schon ein themenfremdes Placebo hob die Erfolgsquote.

## Was sich gegenüber dem Pilot ändert

1. **Codegerüst.** Jede Aufgabe enthält im Prompt ein Gerüst mit Klasse,
   Methodensignaturen, Docstrings und `raise NotImplementedError`, ohne Lösungslogik,
   für alle Bedingungen gleich. Methodennamen können so nicht abweichen.
2. **Keine Kommandozeile.** Sie verursachte im Pilot viele uneinheitliche Fehlschläge
   ohne Bezug zur Frage.
3. **Zwei Fehlertypen, gekreuzt.** Jede Aufgabe enthält genau eine Falle. Jede Erfahrung
   ist für die jeweils andere Gruppe die unpassende Vergleichserfahrung; das ersetzt das
   themenfremde Placebo.
4. **Positivkontrolle.** Ein getrennter Vorlauf prüft, ob 12B die Zielprüfung mit
   direkter Anweisung überhaupt besteht. Eine Aufgabe, die dafür zu schwer ist, kommt
   nicht in den Hauptversuch.
5. **Gegenfälle, in denen Schaden sichtbar ist.**

## Fehlertypen und Aufgaben

**Falle A, Schlüssel:** Nach `json.load` sind Objektschlüssel Strings. Aufgaben der
Gruppe A speichern Einträge unter ihrer ID als Schlüssel (`{"next_id", "items":
{"<id>": …}}`), IDs sind `int`. Ihre Parameter sind nur Texte, damit Falle B nicht
vorkommt. Vier Aufgaben: [zitate, geschenkideen, vokabeln, filmliste].

**Falle B, Wahrheitswerte:** `isinstance(True, int)` ist wahr. Aufgaben der Gruppe B
speichern als Liste (keine ID-Schlüssel, Falle A kommt nicht vor) und verlangen ganze
Zahlen größer 0, wobei die Spezifikation Wahrheitswerte ausdrücklich ausschließt. Vier
Aufgaben: [trainingslog, punktestand, pflanzen, budget].

**Gegenfall A:** Schlüssel sind Postleitzahlen als Text (`"01067"`). Wer sie in `int`
umwandelt, verliert die führende Null. [postleitzahlen]

**Gegenfall B:** Ein Feld ist ausdrücklich ein Wahrheitswert (`active: bool`). Wer
Wahrheitswerte pauschal ablehnt, lehnt dort `True` ab. [gewohnheiten]

## Bedingungen

| Kürzel | Inhalt von `gedaechtnis` | Wo |
|---|---|---|
| O | leer | Vorlauf, Hauptlauf, Gegenfälle |
| A | Erfahrung zu Falle A | Hauptlauf, Gegenfälle |
| B | Erfahrung zu Falle B | Hauptlauf, Gegenfälle |
| D | direkte Anweisung zur Falle der jeweiligen Aufgabe (Positivkontrolle) | nur Vorlauf |

Erfahrung A: Problem „Nach json.load sind Objektschlüssel immer Strings, auch wenn sie
als Zahlen gespeichert wurden.“ Lösung „Beim Laden numerische Schlüssel in int
umwandeln, wenn das Programm mit int-IDs arbeitet.“ Erfahrung B: Problem „In Python sind
True und False auch int; isinstance(True, int) ist wahr.“ Lösung „Wenn nur ganze Zahlen
erlaubt sind, Wahrheitswerte vorher ausdrücklich ablehnen.“ Beide werden im Baupaket auf
genau gleiche Länge gebracht, ohne die Aussage zu ändern. Sie sind einfach und konkret,
enthalten aber keinen fertigen Code (Abwägung: je konkreter, desto mehr Anleitung statt
übertragbarer Erfahrung).

D nennt die Lösung des Teilproblems direkt, etwa „Wandle beim Laden in `__init__` die
Schlüssel von `items` mit `int()` um“ bzw. „Lehne einen Wert ab, wenn `type(wert) is not
int`“. D ist kein Untersuchungsgegenstand, sondern prüft nur die Machbarkeit.

Die Prompts aller Bedingungen unterscheiden sich nur im Feld `gedaechtnis` (wird getestet).

## Messung

- **Mechanismus (Zielprüfung), je Aufgabe genau eine:** A: nach dem Neuladen sind IDs
  `int`, Ändern und Löschen per `int`-ID wirken, die nächste ID stimmt. B: `add(…, True)`
  und `add(…, False)` lösen `ValueError` aus, `add(…, 1)` gelingt. Die Zielprüfung ruft
  nur Gerüstmethoden auf und hängt nicht vom Rest der Aufgabe ab.
- **Gesamtfunktion (übrige Prüfungen), getrennt gemessen:** leere Eingaben, unbekannte
  IDs bzw. Indizes, beschädigte Datei bleibt erhalten, Texte nach Neuladen, eine
  aufgabenspezifische Prüfung. Sie hängen nicht von der Falle ab; ein Selbsttest mit
  Referenzlösungen, die genau die Falle enthalten, belegt das wie im Pilot.
- **Gegenfall:** Zielprüfung „Schlüssel bleiben `"01067"` usw.“ bzw. „`active=True` wird
  angenommen und gespeichert“.

## Ablauf

### Vorlauf (Machbarkeit, eigene Seeds [2001–2005], nicht Teil des Hauptergebnisses)

Je Aufgabe der Gruppen A und B: O und D mit je 5 Seeds; Gegenfälle nur O mit 5 Seeds.

Entscheidung **je Aufgabe**, vorab festgelegt, Nenner jeweils die 5 geplanten Läufe:

| Gate | Bedingung | Regel |
|---|---|---|
| G1 lösbar | D | Zielprüfung in mindestens 4 von 5 bestanden |
| G2 Spielraum | O | Zielprüfung in höchstens 3 von 5 bestanden |
| G3 Rest lösbar | O | übrige Prüfungen zusammen mindestens 80 % bestanden |
| G4 Gegenfall machbar | O, Gegenfall | Zielprüfung in mindestens 4 von 5 bestanden |

Eine Aufgabe kommt in den Hauptlauf, wenn sie G1–G3 erfüllt. Eine **Gruppe** ist
auswertbar, wenn mindestens 3 ihrer 4 Aufgaben eingeschlossen sind; sonst endet v2 in
dieser Fassung (neue Planfassung mit neuen Aufgaben und Seeds nötig). Ein Gegenfall, der
G4 verfehlt, wird im Hauptlauf weiter ausgeführt, seine Schadensgrenze gilt dann aber als
nicht prüfbar und wird so berichtet.

**Fehlende und technisch ungültige Läufe:** Technische Ausfälle (HTTP-Fehler,
abgeschnittene Antwort) zählen in allen Gates als **nicht bestanden**; für G2 ist das
nicht konservativ, deshalb gilt zusätzlich: Liegen im Vorlauf mehr als 10 % der geplanten
Läufe technisch ausgefallen oder fehlen Läufe, ist der Vorlauf ungültig und v2 endet in
dieser Fassung. Kein Lauf wird wiederholt; die Auswahl der Aufgaben geschieht nur nach
diesen Regeln, nie nach Hauptlaufdaten.

### Hauptlauf (eigene Seeds [2101–2115])

Je eingeschlossener Aufgabe O, A und B mit je 15 Seeds; Reihenfolge der Paare und der
Bedingungen je Paar zufällig, durch einen eingefrorenen Startwert festgelegt.
Gegenfälle: O, A und B mit je 10 Seeds [2201–2210].

**Gültigkeit:** wie im Pilot. Die Läufe entsprechen exakt dem Zeitplan, sind vollständig,
ohne Dubletten und fremde Läufe, und höchstens 10 % der geplanten Läufe sind technisch
ausgefallen (Vereinigung aus HTTP-Fehler und Abbruch). Ungültig heißt nie bestanden.

## Erfolgskriterium (vorab, gesamte Regel)

„Passend“ heißt A auf Gruppe-A-Aufgaben und B auf Gruppe-B-Aufgaben, „unpassend“
umgekehrt. Ein Paar ist (Aufgabe, Seed). Bestanden ist der Hauptversuch nur, wenn
**alle** Teile gelten:

1. Gepoolter Abstand der Zielquote passend − unpassend mindestens **20 Prozentpunkte**,
   exakt (vor Rundung) über alle eingeschlossenen Aufgaben.
2. Einseitiger exakter McNemar-Test über alle Paare (passend gegen unpassend) p < 0,05.
3. In jeder Gruppe ist die Summe passend größer als unpassend.
4. Je Gruppe hat höchstens eine eingeschlossene Aufgabe passend < unpassend.

**Schadensgrenzen** (verletzt heißt nicht bestanden):

- Übrige Prüfungen unter passend höchstens 10 Prozentpunkte unter O (gepoolt).
- Gegenfall A: Fehlschläge der Zielprüfung unter A höchstens 2 mehr als unter O (von 10).
  Gegenfall B: unter B höchstens 2 mehr als unter O. Nur prüfbar, wenn G4 erfüllt ist.

**Vorab benannte Nebenauswertungen** (beschreibend, kein Teil des Erfolgs):
unpassend gegen O (unspezifischer Effekt eines gefüllten Felds) und die Lage von passend
zwischen O und der Positivkontrolle D aus dem Vorlauf (Anteil des Spielraums, den die
Erfahrung ausschöpft; Vorlauf und Hauptlauf haben verschiedene Seeds, daher nur grob).

## Trennschärfe der gesamten Regel (simuliert)

[`examples/transfer-v2/simulation.py`](../../examples/transfer-v2/simulation.py), 4000
Simulationen je Zelle. Modell: Rate unter unpassender Erfahrung je Aufgabe N(30 %, 15 %),
wahrer Effekt je Aufgabe N(D, SD), Gauß-Copula mit ρ = 0,3 je Paar, beide Gruppen.
Werte: nur McNemar / gesamte Regel 1–4.

| Aufgaben je Gruppe | Seeds je Aufgabe | D | SD | Trennschärfe |
|---:|---:|---:|---:|---:|
| 4 | 10 | 0 % | 15 % | 0,08 / 0,01 |
| 4 | 10 | 30 % | 15 % | 0,98 / 0,87 |
| 4 | 15 | 0 % | 0 % | 0,04 / 0,00 |
| 4 | 15 | 0 % | 15 % | 0,11 / 0,00 |
| 4 | 15 | 20 % | 15 % | 0,91 / 0,49 |
| 4 | 15 | 30 % | 0 % | 1,00 / 0,97 |
| 4 | 15 | 30 % | 15 % | 1,00 / 0,89 |
| 4 | 15 | 40 % | 15 % | 1,00 / 0,99 |
| 4 | 20 | 30 % | 15 % | 1,00 / 0,91 |
| 3 | 15 | 0 % | 15 % | 0,11 / 0,01 |
| 3 | 15 | 30 % | 15 % | 0,98 / 0,88 |

Empfindlichkeit (4 Aufgaben je Gruppe, 15 Seeds, SD 15 %): bei D = 30 % gesamte Regel
0,88 (ρ = 0), 0,91 (ρ = 0,6), 0,86 (Grundrate 50 %), 0,93 (Grundrate 15 %); bei D = 0
stets 0,00.

Lesart: Ein wahrer Effekt genau in Höhe der Mindestschwelle (20 pp) wird nur etwa jedes
zweite Mal erkannt; ausgelegt ist der Versuch auf Effekte ab etwa 30 pp, die er mit
15 Seeds zu etwa 0,9 erkennt, auch wenn eine Aufgabe je Gruppe ausfällt. Der
McNemar-Test allein wäre bei aufgabenabhängigen Effekten zu großzügig (0,11 ohne
Effekt), weil die Paare über Aufgaben geclustert sind; die Regeln 3 und 4 fangen das ab.
Schadensgrenzen sind nicht simuliert und senken die Trennschärfe weiter.

## Aufwand für 12B

Mit etwa 27 s je Lauf (Pilot): Vorlauf 8 × 2 × 5 + 2 × 5 = 90 Läufe (rund 40 min);
Hauptlauf höchstens 8 × 3 × 15 = 360 Läufe (rund 2 h 45 min) plus Gegenfälle 2 × 3 × 10
= 60 Läufe (rund 30 min). Zusammen höchstens 510 Läufe, rund 3 h 50 min GPU-Zeit, in
Stufen mit Pausen dazwischen. Modell, Digest und Einstellungen wie im Pilot.

## Grenzen

- Zwei Fehlertypen zeigen höchstens, ob gezielter Transfer in sauberen Fällen
  funktioniert, nicht, dass er allgemein funktioniert. Ergebnis nur für 12B.
- Das Gerüst verändert die Aufgabe gegenüber dem Pilot; Ergebnisse sind nicht direkt
  vergleichbar.
- Die Auswahl der Aufgaben über den Vorlauf kann die Grundrate im Hauptlauf verschieben
  (Regression zur Mitte). Deshalb ist der Vergleich passend gegen unpassend im
  Hauptlauf primär, nicht gegen O.
- Die Gegenfälle mit 10 Läufen sind nur grob; ein Einhalten belegt keine Unschädlichkeit.
- Generierter Code läuft ohne Sandbox wie im Pilot.

## Offene Punkte für das Baupaket

- Aufgabennamen und Spezifikationen, Gerüste, Referenzlösungen und Selbsttest
  (Referenz mit genau einer Falle besteht alle übrigen Prüfungen).
- Erfahrungen A und B auf gleiche Länge bringen; Wortlaut von D je Gruppe.
- Seeds und Startwert der Reihenfolge eintragen.
- Host aus dem Pilot übernehmen und anpassen (Gerüst im Prompt, keine CLI, Vorlauf mit
  Gate je Aufgabe, Hauptlauf nur mit gültigem Vorlauf desselben Commits).
