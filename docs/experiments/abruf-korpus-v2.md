# Abrufkorpus v2: Wortformen gefunden, weniger Beifang, ein Regressionskriterium verfehlt

Ausgeführt am 1. November 2026 nach dem vorab festgelegten [Plan](abruf-korpus-v2-plan.md)
(Commit `67a1c4e`, gepusht vor jeder Änderung am Suchcode).
[Korpus v2](../../examples/retrieval/corpus-v2.json), [Auswerteskript](../../examples/retrieval/run.py),
[alle Rohdaten](data/abruf-korpus-v2-20261101/) (Basis und neu, v1 und v2, je beide Läufe).

| Programm | Stand | SHA-256 |
|---|---|---|
| Basis | main `08a8024` (Suchcode wie `cefd87d`) | `54359e04…2c49` |
| Neu | `56888ef` (dieser Branch) | `214abe44…71a7` |

Kein Sprachmodell beteiligt. Beide Korpora sind synthetisch und von einer KI (Claude)
geschrieben; der Autor kannte beim Schreiben von v2 die geplante Richtung.

## Änderung

Teilwortsuche über einfache Wortstämme (höchstens eine Endung `ern`, `en`, `er`, `es`,
`e`, `n`, `s`, mindestens vier Zeichen bleiben), mehr Füllwörter einschließlich
Verneinungen, und eine Mindestabdeckung: Ein Treffer muss mindestens halb so viele
Suchwörter enthalten wie der beste. Filter, Limit und Rangfolge sonst unverändert,
keine Schemaänderung.

## Harte Kriterien: bestanden

In allen vier Läufen (v1 und v2, Basis und neu) keine Bereichs-, Status- oder
Verbotslecks; die beiden Wiederholungen je Lauf sind identisch.

## Ergebnis nach den vorab festgelegten Kriterien

| | Kriterium | Basis | Neu | |
|---|---|---:|---:|---|
| K1 | v2 `wortform_lang` Treffer@5 ≥ 8/10 | 0/10 | 8/10 | erfüllt |
| K2 | v2 `getrennt` Treffer@1 ≥ 6/7 | 1/7 | 6/7 | erfüllt |
| K3 | v2 `wortform_kurz`, `englisch`, `negation`, `bereich`: kein Verlust an Treffer@1 | 11/11 | 11/11 | erfüllt |
| K4 | v2 unpassende Treffer je Frage mit Soll kleiner | 0,29 | 0,11 | erfüllt |
| K5 | v2 `kein_treffer` mittlere Trefferzahl nicht größer | 2,50 | 0,33 | erfüllt |
| R1 | v1 `wortgleich` 10/10 und `ablenker` 6/6 auf Platz 1 | 10 + 6 | 10 + 6 | erfüllt |
| R2 | v1: kein vorher gefundener Eintrag geht verloren | – | 2 verloren | **verfehlt** |
| R3 | v1 unpassende Treffer je Frage mit Soll nicht größer | 2,61 | 0,55 | erfüllt |

**Damit gilt die Änderung nach dem Plan nicht als bestandene Verbesserung.**

Die beiden erwarteten Fehlschläge traten ein: „Passwörter“ (Umlaut-Plural) und „Indizes“
(unregelmäßig) finden ihren Eintrag nicht. In `getrennt` verwechselt „Rechnern“ (Stamm
„rechn“) wie vorhergesagt Rechner und Rechnung: Die Rechnung steht auf Platz 1, der
Rechner auf Platz 2.

## v1 im Einzelnen

| Kategorie | Treffer@1 Basis → neu | Treffer@5 Basis → neu |
|---|---:|---:|
| wortgleich | 10 → 10 | 10 → 10 |
| ablenker | 6 → 6 | 6 → 6 |
| wortform | 3 → 5 | 3 → 5 |
| umformuliert | 5 → 3 | 5 → 4 |
| Positivfälle bereich/status | 4 → 4 | 4 → 4 |

Fragen ohne passenden Eintrag (`kein_treffer`): mittlere Trefferzahl 1,83 → 1,17.

## Nachträgliche Ursachenanalyse (nicht vorab geplant)

Einzelwortabfragen mit beiden Programmen gegen die v1-Datenbank zeigen:

- **Verloren (R2):** q13 („Nach Beginn der Sommerzeit stimmen die Uhrzeiten im Report
  nicht“) und q15 („Kommazahlen bei Preisen werden ungenau addiert“). Mit dem alten
  Programm traf keines ihrer Inhaltswörter den erwarteten Eintrag. Gefunden wurden sie
  nur über die Füllwörter „nach“ und „bei“, die jetzt ignoriert werden. Das Kriterium R2
  unterschied nicht, ob ein früherer Treffer zufällig zustande kam; nach dem Plan ist
  es trotzdem verfehlt.
- **Rang verschlechtert:** q11 (Rang 1 → 3). „eines“ ist kein Füllwort und wird zum
  Stamm „eine“ gekürzt, der in vielen Einträgen steckt („einen“, „Einlesen“). Gebeugte
  Funktionswörter erzeugen so neuen Beifang; das ist eine Schwäche des neuen Verfahrens.
- **Gewonnen:** q17 (umformuliert) sowie q21 und q22 (Wortformen), jetzt über das
  gebeugte Inhaltswort selbst.

## Einordnung

- Der Kern der Änderung wirkt wie beabsichtigt: Längere gebeugte Formen werden gefunden
  (v2: 0 → 8 von 10; v1-Wortformen: 3 → 5, jetzt über das richtige Wort), und der
  Beifang sinkt deutlich (v1: 2,61 → 0,55 je Frage mit Soll).
- Die Verluste betreffen umformulierte Fragen, die vorher nur zufällig über Füllwörter
  trafen. Wer solche Fragen stellt, bekommt jetzt eher eine leere Liste als einen
  zufällig passenden Eintrag.
- Neu entdeckte Schwäche: gebeugte Funktionswörter („eines“) werden zu sehr kurzen
  Stämmen. Eine Korrektur müsste an einem neuen Korpus (v3) geprüft werden, nicht an
  v1 oder v2.
- Ob die Änderung trotz verfehltem R2 übernommen wird, ist eine Abwägung für die
  Prüfung durch Codex und den Projektinhaber, kein Ergebnis dieses Laufs.

## Grenzen

Beide Korpora stammen vom selben Autor, sind klein (28 bzw. 32 Einträge) und
synthetisch. Ein Korpus aus echten Fehlern und echten Fragen fehlt weiterhin.
