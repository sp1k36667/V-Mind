# Plan: Transfer v2 mit Gemma 4 12B (gekreuzte Erfahrungen)

**Status: Plan und Bau zur Prüfung durch Codex (#194). Nicht eingefroren, kein
Modelllauf.** Grundlage: Ergebnis und Grenzen des ersten Pilots
([transfer-pilot.md](transfer-pilot.md)) und die Abstimmung im Teamkanal (#182–#195).
Aufgaben, Prüfungen, Host und Auswertung: [`examples/transfer-v2/`](../../examples/transfer-v2/);
alle festen Werte stehen in `bedingungen.json` und `aufgaben.py`.

## Frage und Zielpopulation

Verhindert eine passende Erfahrung im Prompt bei Gemma 4 12B gezielt den Fehler, auf
den sie sich bezieht, und zwar deutlich besser als eine unpassende Erfahrung gleicher
Art? Und schadet sie dort, wo die Regel nicht gilt?

Die Aussage gilt nur für **die in diesem Plan festgelegten Aufgaben, die die
Vorlaufregeln erfüllen**, für dieses Modell und diese Einstellungen. Sie ist keine
Aussage über Aufgaben allgemein und keine über andere Modelle.

Der erste Pilot konnte das nicht trennen: Ein Benennungsfehler ohne Bezug zur Erfahrung
verdeckte die Messung, und schon ein themenfremdes Placebo hob die Erfolgsquote.

## Was sich gegenüber dem Pilot ändert

1. **Codegerüst.** Jede Aufgabe enthält im Prompt ein Gerüst mit Klasse,
   Methodensignaturen, Docstrings und `raise NotImplementedError`, ohne Lösungslogik,
   für alle Bedingungen gleich.
2. **Keine Kommandozeile.** Sie verursachte im Pilot viele uneinheitliche Fehlschläge
   ohne Bezug zur Frage.
3. **Zwei Fehlertypen, gekreuzt.** Jede Aufgabe enthält genau eine Falle. Jede Erfahrung
   ist für die jeweils andere Gruppe die unpassende Vergleichserfahrung.
4. **Positivkontrolle.** Ein getrennter Vorlauf prüft, ob 12B die Zielprüfung mit
   direkter Anweisung besteht. Zu schwere Aufgaben kommen nicht in den Hauptlauf.
5. **Gegenfälle, in denen Schaden sichtbar ist.**

## Fehlertypen und Aufgaben

**Falle A, Schlüssel:** Nach `json.load` sind Objektschlüssel Strings. Aufgaben der
Gruppe A speichern Einträge unter ihrer ID als Schlüssel (`{"next_id", "items":
{"<id>": …}}`), IDs sind `int`; Parameter sind nur Texte, damit Falle B nicht vorkommt.

**Falle B, Wahrheitswerte:** `isinstance(True, int)` ist wahr. Aufgaben der Gruppe B
speichern als Liste (Falle A kommt nicht vor) und verlangen ganze Zahlen größer 0, wobei
die Spezifikation Wahrheitswerte ausdrücklich ausschließt.

Je Gruppe gibt es **6 Kandidaten in dieser festgelegten Reihenfolge**: A: zitate,
geschenkideen, vokabeln, filmliste, rezeptideen, reiseziele; B: trainingslog,
punktestand, pflanzen, budget, lesezeit, wasserzaehler. In den Hauptlauf kommen je Gruppe
die **ersten 4** Kandidaten dieser Reihenfolge, die die Vorlaufregeln erfüllen.
Spezifikation und Gerüst jeder Aufgabe werden aus einer Tabelle (`aufgaben.py`) erzeugt.

**Gegenfall A (postleitzahlen):** Schlüssel sind Postleitzahlen als Text (`"01067"`);
eine Umwandlung in `int` verliert die führende Null.
**Gegenfall B (gewohnheiten):** Ein Feld ist ausdrücklich ein Wahrheitswert
(`active: bool`); wer Wahrheitswerte pauschal ablehnt, lehnt dort `True` ab.

## Bedingungen

| Kürzel | Inhalt von `gedaechtnis` | Wo |
|---|---|---|
| O | leer | Vorlauf, Hauptlauf, Gegenfälle |
| A | Erfahrung zu Falle A | Hauptlauf, Gegenfälle |
| B | Erfahrung zu Falle B | Hauptlauf, Gegenfälle |
| D | direkte Anweisung zur Falle der jeweiligen Aufgabe (Positivkontrolle) | nur Vorlauf |

Erfahrung A: Problem „Nach json.load sind Objektschlüssel immer Strings, auch wenn sie
als Zahlen gespeichert waren.“ Lösung „Beim Laden numerische Schlüssel in int umwandeln,
wenn das Programm mit int-IDs arbeitet.“ Erfahrung B: Problem „In Python sind True und
False auch ganze Zahlen; isinstance(True, int) ist daher wahr.“ Lösung „Wenn nur ganze
Zahlen erlaubt sind, Wahrheitswerte vor der Prüfung auf int ausdrücklich ablehnen.“ Beide
sind genau 183 Zeichen lang (getestet), einfach und konkret, aber ohne fertigen Code (je
konkreter, desto mehr Anleitung statt übertragbarer Erfahrung).

D steht als Satz „Wichtig: …“ am Ende der Aufgabe (nicht im Feld `gedaechtnis`) und nennt
die Lösung des Teilproblems direkt: A „Wandle beim Laden die Schlüssel von "items" mit
int() in Ganzzahlen um …“, B „Lehne einen Zahlenwert mit ValueError ab, wenn type(wert) is
not int gilt …“. **D dient nur der Machbarkeitsprüfung.** Aus D wird keine Obergrenze und kein relativer Wert
für den Hauptlauf abgeleitet.

Die Prompts von O, A und B unterscheiden sich nur im Feld `gedaechtnis`; D unterscheidet
sich nur durch den angehängten Satz (getestet).

## Messung

- **Mechanismus (Zielprüfung `test_ziel_mechanismus`), je Aufgabe genau eine, mit drei
  Ausgängen:** *bestanden*, *verfehlt* (der Mechanismus wurde erreicht und ist falsch) oder
  *nicht beobachtbar* (App nicht ladbar, Konstruktor oder `list()` scheitern, bevor der
  Mechanismus erreicht ist; Meldung „Vorbedingung: …“). Nur *bestanden* zählt als
  Bestehen; *nicht beobachtbar* wird je Bedingung getrennt berichtet.
  - A, **isolierte Ladeprobe:** Die Prüfung schreibt selbst eine Datei im
    vorgeschriebenen Format mit drei Einträgen und öffnet sie. Vorbedingung: Öffnen und
    `list()` liefern die drei Texte. Mechanismus: IDs sind `int` 1, 2, 3; Ändern und
    Löschen per `int`-ID wirken; die nächste ID ist 4. So hängt das Ergebnis nicht davon
    ab, wie die App selbst speichert.
  - B: Vorbedingung `add(…, 1)` gelingt und erscheint in `list()`. Mechanismus: `add(…,
    True)` löst `ValueError` aus und wird nicht gespeichert. `False` scheitert schon an
    „größer 0“ und wird deshalb nur als **getrennte Diagnose** ausgewiesen.
  - Gegenfall A: Ladeprobe mit `"01067"` und `"10115"`; Mechanismus: Postleitzahlen
    bleiben unverändert, `city("01067")` stimmt, ein neuer Eintrag bleibt Text.
    Gegenfall B: `active=True` und `False` werden angenommen und gespeichert.
- **Gesamtfunktion (übrige Prüfungen), getrennt gemessen:** A und B je 5 (leere Eingaben,
  unbekannte ID bzw. Index, ungültige Zahlen (B), beschädigte Datei bleibt erhalten, Texte
  bzw. Summe nach Neuladen, Format (A)), Gegenfälle je 4. Der Selbsttest belegt mit
  Referenzlösungen, die genau die Falle enthalten, dass sie nicht von der Falle abhängen
  (*verfehlt*, alle übrigen bestanden), dass umbenanntes `list()` und ein Syntaxfehler
  *nicht beobachtbar* ergeben und dass Mutationen der übrigen Anforderungen erkannt werden.

## Ablauf

### Vorlauf (Machbarkeit; eigene Seeds 2001–2008; nicht Teil des Hauptergebnisses)

Je Kandidat: O und D mit je 8 Seeds. Gegenfälle: O mit 8 Seeds.

Entscheidung **je Kandidat**, vorab festgelegt; Nenner sind immer die 8 geplanten Läufe:

| Gate | Bedingung | Regel |
|---|---|---|
| G1 lösbar | D | Zielprüfung in mindestens 6 von 8 bestanden |
| G2 Spielraum | O | Zielprüfung in höchstens 4 von 8 bestanden |
| G3 Rest lösbar | O | übrige Prüfungen zusammen mindestens 80 % über die technisch gültigen O-Läufe |
| G4 Gegenfall prüfbar | O, Gegenfall | Zielprüfung in mindestens 6 von 8 bestanden |

Auswahlwahrscheinlichkeit eines Gates bei wahrer Rate p (Binomial, 8 Läufe):

| wahre Rate p | 50 % | 60 % | 70 % | 80 % | 90 % | 95 % |
|---|---:|---:|---:|---:|---:|---:|
| G1/G4 erfüllt (≥ 6 von 8) | 0,14 | 0,32 | 0,55 | 0,80 | 0,96 | 0,99 |

| wahre Rate p unter O | 10 % | 30 % | 50 % | 60 % | 70 % | 80 % |
|---|---:|---:|---:|---:|---:|---:|
| G2 erfüllt (≤ 4 von 8) | 1,00 | 0,94 | 0,64 | 0,41 | 0,19 | 0,06 |

Mit 5 Läufen wären die Gates zu grob (eine unter D zu 80 % lösbare Aufgabe fiele in 26 %
der Fälle heraus, eine mit 70 % unter O käme zu 47 % durch); deshalb 8.

- Ein Kandidat ist **eingeschlossen**, wenn er G1–G3 erfüllt. Je Gruppe zählen die ersten
  4 eingeschlossenen in der festgelegten Reihenfolge. Hat eine Gruppe weniger als 3
  eingeschlossene, **endet v2 ohne Ergebnis** (keine Wiederholung; eine neue Planfassung
  mit neuen Kandidaten und Seeds wäre nötig).
- Verfehlt ein Gegenfall G4, endet v2 ebenfalls **ohne Gesamtergebnis**: Ein nicht
  prüfbarer Gegenfall kann keinen Gesamterfolg ergeben.
- **Fehlende und technisch ungültige Läufe** (HTTP-Fehler, abgeschnittene Antwort):
  in **G1 und G4 nicht bestanden**; in **G2 zählt ein technischer Ausfall wie ein
  Bestehen** (konservativ: er kann G2 nie künstlich erfüllen); **G3** wird über die
  technisch gültigen O-Läufe berechnet (ohne gültigen Lauf nicht erfüllt). Sind mehr als
  10 % der geplanten Vorlaufläufe technisch ausgefallen oder fehlen Läufe, ist der Vorlauf
  ungültig und v2 endet ohne Ergebnis. Kein Lauf wird wiederholt; die Auswahl geschieht
  nur nach diesen Regeln, nie nach Hauptlaufdaten.

### Hauptlauf (eigene Seeds 2101–2115)

Je eingeschlossener Aufgabe O, A und B mit je 15 Seeds; Reihenfolge der Paare und der
Bedingungen je Paar zufällig, durch einen eingefrorenen Startwert festgelegt.
Gegenfälle: O, A und B mit je 20 Seeds 2201–2220.

**Gültigkeit** wie im Pilot: Die Läufe entsprechen exakt dem Zeitplan, vollständig, ohne
Dubletten und fremde Läufe, höchstens 10 % technische Ausfälle (Vereinigung aus
HTTP-Fehler und Abbruch). Ungültig heißt nie bestanden.

## Erfolgskriterium (vorab, gesamte Regel)

„Passend“ heißt A auf Gruppe-A-Aufgaben und B auf Gruppe-B-Aufgaben, „unpassend“
umgekehrt. Ein Paar ist (Aufgabe, Seed). **Gesamterfolg** nur, wenn der Vorlauf gültig
ist, beide Gruppen auswertbar sind, beide Gegenfälle G4 erfüllen, Hauptlauf und
Gegenfälle gültig sind und **alle** folgenden Teile gelten:

1. Gepoolter Abstand der Zielquote passend − unpassend mindestens **20 Prozentpunkte**,
   exakt (vor Rundung) über alle eingeschlossenen Aufgaben.
2. Einseitiger McNemar-Test über alle Paare (passend gegen unpassend), p < 0,05. Der
   Test ist exakt, wenn alle Paare austauschbar sind; bei Effekten, die je Aufgabe
   verschieden sind (gemischte Nullhypothese), ist er nur eine Näherung und für sich
   allein zu großzügig (simuliert 0,11 statt 0,05). Die Regeln 3 und 4 sind deshalb Teil
   des Kriteriums, und die Fehlerrate der gesamten Regel ist unten simuliert.
3. In jeder Gruppe ist die Summe passend größer als unpassend.
4. Je Gruppe hat höchstens eine eingeschlossene Aufgabe passend < unpassend.
5. **Schaden übrige Prüfungen:** Anteil unter passend höchstens 10 Prozentpunkte unter O
   (gepoolt, exakt).
6. **Schaden Gegenfälle:** In Gegenfall A Fehlschläge der Zielprüfung (verfehlt oder
   nicht beobachtbar) unter A höchstens 3 mehr als unter O (von je 20); in Gegenfall B
   unter B höchstens 3 mehr als unter O. Beide Ausgänge werden getrennt berichtet.

Begründung der Gegenfallgrenze (simuliert, Grundrate unter O 90 %, je Gegenfall):

| Seeds | Grenze | verletzt ohne Schaden | erkannt bei 20 pp Schaden | erkannt bei 30 pp Schaden |
|---:|---:|---:|---:|---:|
| 10 | +1 | 0,12 | 0,62 | 0,80 |
| 10 | +2 | 0,03 | 0,38 | 0,61 |
| 15 | +3 | 0,02 | 0,41 | 0,68 |
| 20 | +3 | 0,03 | 0,58 | 0,83 |
| 20 | +4 | 0,01 | 0,41 | 0,72 |

20 Seeds mit Grenze +3 halten Fehlalarme ohne Schaden bei etwa 3 % und erkennen einen
Schaden von 30 Prozentpunkten zu 0,83; toleriert wird damit ein beobachteter
Mehrschaden bis 15 Prozentpunkte. Ein kleinerer Schaden (20 pp) wird nur etwa zur Hälfte
erkannt; ein Einhalten belegt keine Unschädlichkeit.

**Vorab benannte Nebenauswertung** (beschreibend, nicht Teil des Erfolgs): unpassend
gegen O je Gruppe, als Schätzung des unspezifischen Effekts eines gefüllten Felds.

## Trennschärfe (simuliert)

[`examples/transfer-v2/simulation.py`](../../examples/transfer-v2/simulation.py).
Annahmen: Zielrate unter O je Aufgabe N(30 %, 15 %), unspezifischer Effekt +10 pp unter
jeder Erfahrung, wahrer gezielter Effekt je Aufgabe N(D, 15 %), Positivkontrolle je
Aufgabe N(85 %, 10 %), übrige Prüfungen N(90 %, 5 %) je Prüfung, Gegenfälle 90 % unter O,
Gauß-Copula ρ = 0,3 je Paar. Die Annahmen sind Schätzungen; der Vorlauf misst die echten
Raten.

**Bedingt** (nur Hauptvergleich, Regeln 1–4, wenn je Gruppe 4 Aufgaben eingeschlossen
sind; ohne Vorlaufauswahl und ohne Schadensgrenzen; nur McNemar / Regeln 1–4):

| Aufgaben je Gruppe | Seeds | D | SD | bedingte Trennschärfe |
|---:|---:|---:|---:|---:|
| 4 | 15 | 0 % | 15 % | 0,11 / 0,00 |
| 4 | 15 | 20 % | 15 % | 0,91 / 0,49 |
| 4 | 15 | 30 % | 15 % | 1,00 / 0,89 |
| 4 | 15 | 40 % | 15 % | 1,00 / 0,99 |
| 3 | 15 | 30 % | 15 % | 0,98 / 0,88 |

**Vollständige Regel** (Vorlauf mit G1–G4 einschließlich konservativer Behandlung
technischer Ausfälle und Auswahl, Hauptlauf, Schadensgrenzen 5 und 6; 3 % technische
Ausfälle je Lauf angenommen, im Pilot waren es 0 von 170; 2000 Durchführungen je
Szenario; `python3 simulation.py --vollstaendig`):

| Szenario | Gesamterfolg | häufigster Grund sonst |
|---|---:|---|
| Null: kein Effekt, kein unspezifischer Effekt | 0,00 | Hauptkriterium verfehlt |
| Null: nur unspezifischer Effekt +10 pp | 0,00 | Hauptkriterium verfehlt |
| Null: gezielter Effekt je Aufgabe N(0, 15 pp) | 0,00 | Hauptkriterium verfehlt |
| Null, 8 % technische Ausfälle | 0,00 | Hauptkriterium verfehlt |
| Effekt 30 pp, kein Schaden | 0,55 | Gruppe nicht auswertbar |
| Effekt 30 pp, keine technischen Ausfälle | 0,67 | Gruppe nicht auswertbar |
| Effekt 40 pp, kein Schaden | 0,61 | Gruppe nicht auswertbar |
| Effekt 30 pp, Grundrate O 50 % | 0,18 | Gruppe nicht auswertbar |
| Effekt 30 pp, Positivkontrolle nur 75 % | 0,27 | Gruppe nicht auswertbar |
| Effekt 30 pp, 8 % technische Ausfälle | 0,31 | Gruppe nicht auswertbar |
| Effekt 30 pp, nur 4 Kandidaten je Gruppe | 0,21 | Gruppe nicht auswertbar |
| Effekt 30 pp, Schaden übrige 15 pp | 0,01 | Schaden übrige Prüfungen |
| Effekt 30 pp, Schaden Gegenfall 30 pp | 0,01 | Schaden Gegenfall |
| Effekt 30 pp, Schaden Gegenfall 20 pp | 0,10 | Schaden Gegenfall |

Lesart (alles **Ergebnisse dieser Simulation** unter ihren Annahmen, keine allgemeine
Fehlerkontrolle und keine zugesicherte Trennschärfe):

- In den simulierten Nullszenarien, auch wenn jede Erfahrung unspezifisch hilft, der
  Effekt je Aufgabe streut oder 8 % der Läufe technisch ausfallen, trat in 2000
  Durchführungen je Szenario kein Gesamterfolg auf. Für andere, nicht simulierte
  Nullkonstellationen ist damit nichts gesagt.
- Bei einem gezielten Effekt von 30 pp gelang der Nachweis in diesem Szenario zu 0,55
  (ohne technische Ausfälle 0,67). Der Hauptverlust ist die **Machbarkeit**: Zu wenige
  Kandidaten erfüllen die Gates. Dann endet v2 ohne Ergebnis, statt ein falsches zu
  liefern. Technische Ausfälle kosten Machbarkeit, weil G2 sie konservativ zählt; mit nur
  4 Kandidaten je Gruppe wären es 0,21.
- Ist 12B ohne Hilfe schon besser (Grundrate 50 %) oder mit Hilfe schlechter
  (Positivkontrolle 75 %), sinkt die Chance stark, weil G2 bzw. G1 mehr Aufgaben
  ausschließt. Das ist gewollt: Solche Aufgaben messen die Frage nicht sauber.
- Ein Effekt genau an der Mindestschwelle (20 pp) wird auch bedingt nur etwa jedes zweite
  Mal erkannt; ausgelegt ist der Versuch auf Effekte ab etwa 30 pp.

## Aufwand für 12B

Mit etwa 27 s je Lauf (Pilot):

- Vorlauf: 12 Kandidaten × 2 Bedingungen × 8 + 2 Gegenfälle × 8 = 208 Läufe, rund 1 h 35 min.
- Hauptlauf: höchstens 8 Aufgaben × 3 × 15 = 360 Läufe, rund 2 h 45 min.
- Gegenfälle: 2 × 3 × 20 = 120 Läufe, rund 55 min.

Zusammen höchstens 688 Läufe, rund 5 h 15 min GPU-Zeit, in drei Stufen mit Pausen. Endet
v2 nach dem Vorlauf, bleibt es bei 208 Läufen. Modell, Digest und Einstellungen wie im
Pilot.

## Grenzen

- Zwei Fehlertypen zeigen höchstens, ob gezielter Transfer in sauberen Fällen
  funktioniert, nicht, dass er allgemein funktioniert. Ergebnis nur für 12B und die
  eingeschlossenen Aufgaben.
- Das Gerüst verändert die Aufgabe gegenüber dem Pilot; Ergebnisse sind nicht direkt
  vergleichbar.
- Die Auswahl über den Vorlauf kann die Grundrate im Hauptlauf verschieben (Regression
  zur Mitte); deshalb ist passend gegen unpassend primär, nicht gegen O.
- Die Gegenfälle erkennen nur deutliche Schäden; ein Einhalten belegt keine
  Unschädlichkeit.
- Die Simulation beruht auf geschätzten Raten; sie zeigt die Eigenschaften der Regel,
  nicht die Erfolgsaussicht des echten Versuchs.
- Generierter Code läuft ohne Sandbox wie im Pilot.

## Umsetzung (Baupaket)

Seeds: Vorlauf 2001–2008, Hauptlauf 2101–2115, Gegenfälle 2201–2220; Startwert der
Reihenfolge 20261104. Der Host übernimmt die Schutzregeln des Pilots (Digest, nur am
sauberen Commit, keine Wiederholung, gespeicherte Ergebnisse gegen den Zeitplan geprüft,
Anfrage auch bei HTTP-Fehler gespeichert, Zeit- und Ausgabelimit mit Beenden der
Prozessgruppe). Haupt- und Gegenfall starten nur mit einem Vorlauf desselben Commits, der
die Fortsetzung erlaubt; die eingeschlossenen Aufgaben übernimmt der Host aus dessen
Auswertung. `--attrappe` erzeugt ohne Modell einen künstlichen gezielten Effekt, um Host
und Auswertung durchgängig zu prüfen; Attrappenergebnisse sind nie Messdaten.
