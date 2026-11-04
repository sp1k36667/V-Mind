# Plan: Aufgabensuche für Transfer v3 mit Gemma 4 12B

Reine **Vorauswahl** vor einem späteren Transferversuch v3. Sie soll Aufgaben finden, bei
denen 12B die eingebaute Falle ohne Hilfe weder fast immer noch fast nie vermeidet. Sie
liefert **keine Rate und keine Aussage über die Wirkung von Erfahrungen**.

Anlass: Im Transfer-Pilot bestand O die Zielprüfung im Vorlauf 1 von 20 (zu schwer), im
Vorlauf von v2 77 von 96 (zu leicht, [Bericht](transfer-v2-vorlauf.md)). Abstimmung im
Teamkanal #216–#220 (Codex, mit Vorschlägen von Gemini über den Nutzer; Claude #219).
Der Nutzer wünscht einen Beginn mit 10–15 Aufrufen.
Aufbau: [`examples/transfer-v3-suche/`](../../examples/transfer-v3-suche/).

## Aufgaben und Fallen

Zustandsübergänge und präzise Randfälle, je Aufgabe genau ein messbarer Fehler. Die
Reihenfolge ist die feste Priorität bei Gleichstand.

| Priorität | Aufgabe | Schnittstelle | Falle (Zielprüfung) |
|---:|---|---|---|
| 1 | datumsimport | `parse_date(text)` | `datetime.strptime` nimmt „2026-1-5“ an; ungepaddete Daten müssen abgelehnt werden |
| 2 | kalender | `Calendar().reserve(start_min, end_min)`, `bookings()` | `<=` statt `<`: direkt angrenzende Reservierungen werden abgelehnt |
| 3 | warteliste | `Waitlist(capacity)`: `book`, `cancel`, `confirmed`, `waiting` | zweite Stornierung derselben ID wird nicht erkannt |
| 4 | paketstatus | `Package()`: `apply(event)`, `status()` | verspätetes Ereignis stuft „delivered“ zurück |
| 5 | bestellimport | `Importer(path)`: `ingest(event_id, cents)`, `total()` | verarbeitete IDs nur im Speicher; nach Neuöffnen doppelt gezählt |
| 6 | lager | `Stock(initial)`: `deposit`, `withdraw`, `balance()` | Bestand vor der Prüfung verringert; abgelehnte Entnahme ändert ihn |

Die Spezifikation nennt die verlangte Eigenschaft jeweils ausdrücklich (zum Beispiel
„ohne führende Nullen wie "2026-1-5" … ValueError“), damit ein Fehlschlag die Falle misst
und keine Mehrdeutigkeit. Gerüste enthalten nur Signaturen. `event_id` ist Text, damit
der Bestellimport nicht die JSON-Schlüsselfalle des Pilots als Störfehler auslöst.
Lager gilt vorab als vermutlich zu leicht und hat die niedrigste Priorität.

Jede Zielprüfung prüft zuerst eine **Vorbedingung** (Symbol ladbar, vorbereitende Schritte
korrekt). Scheitert sie, ist der Lauf „nicht beobachtbar“, nicht „verfehlt“. Die übrigen
Prüfungen hängen nicht von der Falle ab; das zeigt der Selbsttest mit einer Referenz, die
genau die Falle enthält. Eine Diagnose (`test_diag_kompaktformat_abgelehnt`: „20260105“,
das `date.fromisoformat` ab Python 3.11 annimmt) zählt weder zum Ziel noch zu den übrigen.

## Ablauf

| Stufe | Läufe | Bedingung | Seeds |
|---|---|---|---|
| o | 6 Aufgaben × 2 = 12 | O: ohne Hilfe | 3001, 3002 (Reihenfolge durch Startwert 20261105 gemischt) |
| d | höchstens 3 | D: Spezifikation plus direkte Anweisung | 3101 |

Modell, Digest, Temperatur 0,7 und übrige Optionen wie im Pilot und in v2
(`bedingungen.json`). Die direkten Anweisungen stehen vorab in `bedingungen.json`.
Seeds sind von denen des Pilots und von v2 getrennt; ein späterer Hauptversuch bekommt
wieder eigene Seeds.

**Harte Grenze: 15 Generierungsanfragen** je Ausgabeordner. Jede Anfrage wird vor dem
Senden in `aufrufe.jsonl` angemeldet, also zählen auch fehlgeschlagene. Ein schon
angemeldeter Lauf wird nie erneut gesendet; ein unvollständiger Laufordner stoppt den
Host. Das Entladen des Modells vor jeder Anfrage (`keep_alive: 0`) erzeugt keinen Text
und zählt nicht. Es gibt keine Pflicht, das Budget zu verbrauchen.

## Vorab festgelegte Regel

**Stufe o**, je Aufgabe über ihre 2 Läufe:

- **Technischer Ausfall** (HTTP-Fehler, Zeitüberschreitung, abgeschnittene Antwort) in
  einem der beiden Läufe: Aufgabe nicht beurteilbar, nicht geeignet.
- **Geeignet**, wenn kein technischer Ausfall, die Zielprüfung in mindestens einem Lauf
  „verfehlt“ ist und die übrigen Prüfungen über beide Läufe zusammen mindestens 80 %
  bestehen. Nenner: 2 × Anzahl übriger Prüfungen der Aufgabe; „nicht beobachtbare“ Läufe
  zählen im Nenner mit.
- **Rang** der geeigneten Aufgaben: zuerst gemischt (1 bestanden, 1 verfehlt), danach ohne
  bestandenen Lauf; bei Gleichstand die Priorität oben.
- **Auswahl:** die ersten höchstens 3 nach Rang.

Warum gemischt zuerst (Binomial, 2 Läufe, wahre Bestehensrate p ohne Hilfe):

| p | 5 % (wie Pilot) | 30 % | 50 % | 80 % (wie v2) | 95 % |
|---|---:|---:|---:|---:|---:|
| Fehler mindestens einmal | 1,00 | 0,91 | 0,75 | 0,36 | 0,10 |
| gemischt (1 von 2) | 0,10 | 0,42 | 0,50 | 0,32 | 0,10 |

„Fehler beobachtet“ allein schließt nur zu leichte Aufgaben aus; eine Aufgabe wie im
Pilot käme sicher durch. Der Vorrang für gemischte Ergebnisse bevorzugt den mittleren
Bereich, ohne Aufgaben mit 0 von 2 auszuschließen.

**Stufe d**, je ausgewählte Aufgabe ein Lauf: **bestätigt**, wenn nicht technisch
ausgefallen, Zielprüfung bestanden und übrige Prüfungen mindestens 80 %. Stufe d läuft nur
nach gültiger Stufe o desselben Commits; die Auswahl wird vom Host neu berechnet und mit
der Auswertung abgeglichen.

**Ergebnis:** die Liste der bestätigten Aufgaben als Kandidaten für die Kalibrierung eines
späteren v3-Plans. Sind es keine, ist das ein gültiges Ergebnis.

## Was das Ergebnis nicht zeigt

- Aus 2 Läufen ohne und 1 Lauf mit Hilfe folgt keine Rate. Eine gemischte Aufgabe kann
  wahre Bestehensraten von etwa 10 % bis 90 % haben.
- Nichts über den Nutzen von Erfahrungen oder V-Mind; Erfahrungen kommen nicht vor.
- Der spätere Versuch braucht eigene Kalibrierungsläufe mit getrennten Seeds und vorab
  festgelegte Kriterien; diese Suche ersetzt sie nicht.
- Generierter Code läuft ohne Sandbox wie im Pilot.

## Prüfung ohne Modell

`selbsttest.py`: Referenzen bestehen; die Falle ergibt „verfehlt“ ohne Einfluss auf die
übrigen Prüfungen; umbenanntes Symbol und Syntaxfehler ergeben „nicht beobachtbar“; jede
Mutation wird von der erwarteten übrigen Prüfung erkannt. `test_suche.py`: Zeitplan,
Seeds, Prompts, Eignung, Rang, Nenner, technische Ausfälle, Grenze von 15, keine
Wiederholung, Stufe d nur nach gültiger Stufe o. Gezählte Läufe nur nach unabhängiger
Prüfung und Freeze.
