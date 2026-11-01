# Abrufkorpus v1: Plan (vor dem ersten Abruf festgelegt)

Festgelegt am 1. November 2026, bevor eine einzige Korpusfrage an V-Mind gestellt wurde.
Korpus: [`examples/retrieval/corpus.json`](../../examples/retrieval/corpus.json).

## Frage

Wie gut findet `vmind recall` das passende geprüfte Wissen, und hält es dabei die
zugesagten Grenzen ein: kein Wissen aus fremden Projektbereichen, nichts Ungeprüftes,
nichts Zurückgezogenes?

Dies ist kein Modellversuch. Gemessen wird nur die Suche, ohne Sprachmodell.

## Korpus

- 32 Einträge: 28 validiert (14 `global`, 11 `alpha`, 3 `beta`), 2 ungeprüft
  (`pending`, `alpha`), 2 zurückgezogen (je einer in `alpha` und `global`).
- 45 Fragen in sieben Kategorien:

| Kategorie | Fragen | Was sie prüft |
|---|---:|---|
| `wortgleich` | 10 | Frage teilt markante Wörter mit dem Eintrag (typisch: kopierte Fehlermeldung) |
| `umformuliert` | 8 | gleiche Bedeutung, andere Wörter (Synonyme, Umschreibung) |
| `wortform` | 5 | Beugung und Zusammensetzung (Teilwortsuche) |
| `ablenker` | 6 | ein ähnlicher, aber falscher Eintrag existiert |
| `kein_treffer` | 6 | es gibt keinen passenden Eintrag |
| `bereich` | 6 | richtiger Eintrag liegt im fremden Bereich bzw. globaler Eintrag ist sichtbar |
| `status` | 4 | passender Eintrag ist ungeprüft oder zurückgezogen |

**Einschränkung:** Einträge und Fragen sind synthetisch und von einer KI (Claude)
geschrieben. Sie sind keine Stichprobe echter Projekte, und die Kategorien sind vom
Autor zugeordnet. Die Ergebnisse beschreiben nur diesen Korpus.

## Ablauf

1. Neue leere Datenbank in einem temporären Ordner, nur über die CLI (`init`, `add`,
   `validate`, `invalidate`), Einträge in Dateireihenfolge.
2. Jede Frage einmal mit `vmind --json --scope BEREICH recall DB TEXT` (Limit 5, wie
   in der CLI fest eingestellt). Keine Änderung an Ranking, Stoppwörtern oder Limit.
3. Gesamter Lauf ein zweites Mal mit neuer Datenbank; beide Ergebnislisten müssen
   identisch sein (die Suche ist deterministisch).
4. Rohdaten (alle Trefferlisten) und Auswertung werden unverändert veröffentlicht.

## Harte Kriterien (Produktzusagen)

Über alle 45 Fragen und beide Läufe:

- **Bereichslecks = 0:** kein Treffer aus einem Bereich außer dem abgefragten und `global`.
- **Statuslecks = 0:** kein Treffer mit Status `pending` oder einem Rückzug.
- **Verbotene Treffer = 0:** kein in `forbidden` genannter Eintrag in einer Trefferliste.
- **Reproduzierbarkeit:** beide Läufe liefern dieselben IDs in derselben Reihenfolge.

Verfehlt einer dieser Punkte, gilt die Abnahme als nicht bestanden.

## Kennzahlen (beschreibend)

Für Fragen mit erwartetem Eintrag:

- **Treffer@1:** der erwartete Eintrag steht auf Platz 1.
- **Treffer@5:** der erwartete Eintrag ist unter den (höchstens 5) Treffern.
- **MRR:** Mittelwert von 1/Rang des erwarteten Eintrags (0, wenn nicht gefunden).

Für `ablenker` zusätzlich: Anteil der Fragen, bei denen der erwartete Eintrag vor dem
Ablenker steht (Ablenker nicht gefunden, erwarteter gefunden = vor).

Für Fragen ohne erwarteten Eintrag (`kein_treffer` und die Negativfälle in `bereich` und
`status`): Anteil leerer Trefferlisten und mittlere Zahl zurückgegebener Treffer.
Jeder zurückgegebene Eintrag ist dort ein Fehltreffer, auch wenn er erlaubt ist.

## Vorab notierte Erwartungen (keine Bestehensgrenzen)

- `wortgleich`: Treffer@1 mindestens 9 von 10.
- `wortform`: Treffer@5 mindestens 4 von 5.
- `umformuliert`: deutlich schwächer; die Suche kennt keine Synonyme. Keine Schwelle.
- `kein_treffer`: überwiegend **nicht** leere Listen, weil Suchwörter mit ODER
  verknüpft werden und die Teilwortsuche bis zum Limit auffüllt. Das wäre eine
  dokumentierte Grenze, kein Fehler im Sinne der harten Kriterien.

Nach dem Lauf werden diese Erwartungen nicht angepasst. Fragen oder Einträge werden
nach dem ersten Abruf nicht geändert; ein überarbeiteter Korpus wäre v2 mit neuem Plan.
