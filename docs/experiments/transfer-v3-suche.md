# Aufgabensuche für Transfer v3 mit Gemma 4 12B: kein Kandidat

**Vorab festgelegtes Ergebnis: keine geeignete Aufgabe.** Alle 12 Läufe ohne Hilfe sind
gültig, und in allen 12 hat 12B die Falle vermieden. Nach der Regel ist damit keine
Aufgabe geeignet; die Stufe mit direkter Hilfe fand nicht statt. Die Suche ist eine reine
Vorauswahl und sagt nichts über die Wirkung von Erfahrungen.

Plan: [transfer-v3-suche-plan.md](transfer-v3-suche-plan.md), eingefroren in Commit
`b37abc1`. Aufbau: [`examples/transfer-v3-suche/`](../../examples/transfer-v3-suche/).
Daten: [`data/transfer-v3-suche-20261104/`](data/transfer-v3-suche-20261104/).

## Durchführung

- Modell wie im Pilot und in v2 (Gemma 4 12B, Q4_0, Digest vom Host geprüft),
  Temperatur 0,7. 6 Aufgaben × 2 Seeds (3001, 3002) ohne Hilfe.
- Ausgeführt von Codex am 4. November 2026, 16:37 bis 16:40 Uhr, am sauberen
  Freeze-Commit (Prüfsumme der Bedingungen gleich dem Freeze), eine Host-Instanz,
  9 bis 16 s je Lauf. 12 Generierungsanfragen im Aufrufprotokoll, nur Stufe o; kein Lauf
  wiederholt. Die drei Aufrufe für Stufe d blieben ungenutzt, wie vorgesehen, wenn keine
  Aufgabe geeignet ist.
- Der Lauf fand statt, bevor Claude den Aufbau wie erbeten gelesen hatte. Code und Regel
  waren am Freeze unverändert; am Ergebnis ändert das nichts.
- Auswertung mit dem eingefrorenen `auswerten.py`. Claude hat sie aus
  `git archive b37abc1` unabhängig wiederholt und die Läufe zusätzlich direkt aus den
  Ergebnisdateien gezählt; beides stimmt mit der Meldung von Codex überein. Die abgelegte
  Auswertung ([`auswertung-b37abc1.json`](data/transfer-v3-suche-20261104/auswertung-b37abc1.json))
  ist über die Kopie im Repository erzeugt.

## Vorab festgelegte Auswertung

Geeignet wäre eine Aufgabe nur gewesen, wenn die Zielprüfung in mindestens einem der zwei
Läufe verfehlt worden wäre.

| Aufgabe | Ziel bestanden | Ziel verfehlt | übrige Prüfungen | geeignet |
|---|---:|---:|---:|:-:|
| datumsimport | 2 / 2 | 0 | 8 / 8 | nein |
| kalender | 2 / 2 | 0 | 6 / 8 | nein |
| warteliste | 2 / 2 | 0 | 8 / 10 | nein |
| paketstatus | 2 / 2 | 0 | 10 / 10 | nein |
| bestellimport | 2 / 2 | 0 | 6 / 8 | nein |
| lager | 2 / 2 | 0 | 8 / 8 | nein |

Technische Ausfälle 0, abgeschnittene Antworten 0, nicht beobachtbar 0. Auswahl leer,
kein Lauf mit direkter Hilfe.

## Beschreibende Befunde (nachträglich, kein Kriterium)

**Fehler außerhalb der Fallen.** Wo Läufe Prüfungen verfehlten, lag es nicht an der
eingebauten Falle, sondern an Anforderungen, die die Spezifikation nur allgemein nennt:

- kalender, beide Läufe: eine Kommazahl als Zeit wurde ohne Typprüfung angenommen
  (`test_ungueltige_zeiten_valueerror`).
- bestellimport, beide Läufe: ungültige Werte nicht vollständig abgelehnt
  (`test_ungueltige_werte_valueerror`); in Seed 3001 wurde eine `event_id` nur aus
  Leerzeichen angenommen.
- warteliste, Seed 3002: `confirmed()` blieb nach einer Buchung leer; die
  Bestätigungslogik war fehlerhaft (`test_ids_und_reihenfolge`,
  `test_unbekannte_id_valueerror`).

**Mögliche Erklärung, nicht geprüft:** Die Spezifikationen nennen die Falle ausdrücklich,
meist mit dem typischen Fehlbeispiel („ohne führende Nullen wie "2026-1-5"“, „direkt
aneinandergrenzende Reservierungen … sind erlaubt“, „Das Stornieren einer unbekannten oder
bereits stornierten ID löst ValueError aus“). Für 12B ist das vermutlich schon fast die Lösung. Dazu passt, dass die nicht
hervorgehobenen Details häufiger verfehlt wurden. Belegt ist das mit 12 Läufen nicht;
andere Erklärungen (die Fallen sind für 12B allgemein leicht) sind ebenso möglich.

## Folgerung

Wie im v2-Vorlauf waren die Aufgaben für 12B ohne Hilfe zu leicht, diesmal noch deutlicher.
Eine weitere Suche bräuchte eine neue Planfassung mit neuen Seeds; dieser Lauf wird nicht
wiederholt und seine Regel nicht nachträglich geändert. Naheliegend wäre, die Falle in der
Spezifikation nur als allgemeine Anforderung zu formulieren, ohne Fehlbeispiel, oder Fallen
zu wählen, die sich aus allgemeinen Anforderungen ergeben. Ob das die Schwierigkeit in den
gewünschten Bereich bringt, müsste eine solche Suche erst zeigen.

## Grenzen

- 2 Läufe je Aufgabe: 2 von 2 bestanden ist auch bei einer wahren Bestehensrate von 50 %
  in einem Viertel der Fälle zu erwarten. Die Suche schließt Aufgaben nur nach ihrer Regel
  aus, sie misst keine Raten.
- Die nachträglichen Befunde sind beschreibend und nicht vorab geplant.
- Generierter Code lief ohne Sandbox wie im Pilot.
