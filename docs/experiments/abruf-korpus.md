# Abrufkorpus v1: Grenzen gehalten, Wortformen nicht erkannt, viel Beifang

Ausgeführt am 1. November 2026 nach dem vorab festgelegten
[Plan](abruf-korpus-plan.md) (Commit `be4ff0c`, vor der ersten Abfrage veröffentlicht).
[Korpus](../../examples/retrieval/corpus.json),
[Auswerteskript](../../examples/retrieval/run.py),
[alle Trefferlisten](data/abruf-korpus-20261101/results.jsonl),
[Zusammenfassung](data/abruf-korpus-20261101/summary.json).

Geprüft wurde `vmind recall` von main `cefd87d`, gebaut mit `cargo build --release --locked`
(SHA-256 des Programms `54359e04…2c49`). Kein Sprachmodell beteiligt. Einträge und
Fragen sind synthetisch und von einer KI (Claude) geschrieben; sie sind keine Stichprobe
echter Projekte.

## Harte Kriterien: bestanden

| Kriterium | Ergebnis |
|---|---|
| Treffer aus fremdem Projektbereich | 0 |
| Ungeprüfte oder zurückgezogene Treffer | 0 |
| Ausdrücklich verbotene Einträge in einer Trefferliste | 0 |
| Zwei Läufe mit neuer Datenbank: gleiche IDs in gleicher Reihenfolge | ja |

Das gilt für alle 45 Fragen in beiden Läufen. Die Statusfilter halten auch dann, wenn
der zurückgezogene Eintrag fast wörtlich zur Frage passt (q45: „database is locked
trotz busy_timeout“ liefert den gültigen Eintrag, nicht den zurückgezogenen).

## Kennzahlen

Fragen mit einem erwarteten Eintrag (Limit 5 Treffer):

| Kategorie | Fragen | Treffer@1 | Treffer@5 | MRR |
|---|---:|---:|---:|---:|
| wortgleich | 10 | 10 | 10 | 1,00 |
| ablenker | 6 | 6 | 6 | 1,00 |
| bereich (Positivfälle) | 3 | 3 | 3 | 1,00 |
| status (Positivfall) | 1 | 1 | 1 | 1,00 |
| umformuliert | 8 | 5 | 5 | 0,63 |
| wortform | 5 | 3 | 3 | 0,60 |

Bei allen sechs Ablenkerfragen stand der richtige Eintrag vor dem ähnlichen falschen.

Fragen ohne passenden Eintrag (jeder Treffer ist Beifang):

| Kategorie | Fragen | leere Liste | mittlere Trefferzahl |
|---|---:|---:|---:|
| kein_treffer | 6 | 3 | 1,83 |
| bereich (Negativfälle) | 3 | 2 | 1,67 |
| status (Negativfälle) | 3 | 1 | 3,33 |

## Vergleich mit den vorab notierten Erwartungen

- `wortgleich` Treffer@1 mindestens 9/10: **erfüllt** (10/10).
- `wortform` Treffer@5 mindestens 4/5: **verfehlt** (3/5), und auch diese drei sind
  kein Verdienst der Wortformerkennung (siehe unten).
- `umformuliert`: wie erwartet schwächer (5/8). In den gefundenen Fällen teilte die
  Frage trotz Umformulierung noch einzelne Wörter mit dem Eintrag (etwa „PyTorch“,
  „AMD“), echte Synonyme erkennt die Suche nicht.
- `kein_treffer`: erwartet waren überwiegend nicht leere Listen; tatsächlich 3 von 6
  leer. Die Erwartung war hier zu pessimistisch, die drei Fehlfälle bestätigen aber
  die Ursache (siehe unten).

## Nachträgliche Fehleranalyse (nicht vorab geplant)

Um die Ursachen zu verstehen, wurden die einzelnen Wörter der Wortformfragen danach
noch einmal allein abgefragt. Das ist eine Erkundung, sie ändert keine Wertung.

**1. Gebeugte Formen werden nicht gefunden, wenn die Frage länger ist als das
gespeicherte Wort.** Die Teilwortsuche findet ein Frage-Wort nur, wenn es *im*
gespeicherten Wort steckt. „Rundungsfehler“ findet den Eintrag, „Rundungsfehlern“ nicht;
„Schlüsseldatei“ ja, „Schlüsseldateien“ nicht. Allein abgefragt fand keines der Wörter
„Migrationen“, „Sicherungen“, „Zeitüberschreitungen“, „Rundungsfehlern“, „Geldbetrag“
(gespeichert: „Geldbeträgen“), „Schlüsseldateien“, „Datenbanksicherung“ oder
„Schemamigrationen“ einen Eintrag. Die drei erfolgreichen Wortformfragen trafen über
andere Wörter: „ohne“ (q19), „Ollama“ (q20) und „vor“ (q23). **Wortformen im eigentlichen
Sinn wurden also in 0 von 5 Fällen erkannt.** Die bisherige Beschreibung „findet auch
gebeugte und zusammengesetzte Wörter (zum Beispiel ‚Migration‘ in ‚Schemamigrationen‘)“
stimmt für genau diese Richtung: Die Frage muss die kürzere Form enthalten.

**2. Häufige Wörter fehlen in der Stoppwortliste.** „nicht“ allein liefert fünf
beliebige Einträge, „Datei“ ebenfalls, „vor“ drei. Daraus stammt der größte Teil des
Beifangs bei den Fragen ohne passenden Eintrag (q32 „…verbinden sich nicht…“, q35
„Datei lässt sich nicht umbenennen“).

**3. Viel Beifang neben richtigen Treffern.** Die 33 Fragen mit erwartetem Eintrag
lieferten 114 Treffer, davon 28 richtige, also im Mittel 2,6 unpassende Einträge je
Frage; 12 Listen waren ganz gefüllt. Steht der richtige Eintrag vorn (wie bei allen
wortgleichen Fragen), ist das für einen Menschen harmlos. Ein kleines Modell bekommt
aber diese Einträge mit in den Kontext.

## Was daraus folgt

- Die zugesagten Grenzen (Bereich, Status, Rückzug) halten in diesem Korpus ohne
  Ausnahme. Das ist der wichtigste Befund für die Vertrauenswürdigkeit.
- Wortgleiche Fragen, typischerweise kopierte Fehlermeldungen, funktionieren sehr gut.
- Die Teilwortsuche ist schwächer als bisher beschrieben. README und `docs/cli.md`
  sollten präzisieren, dass sie Teilwörter findet, aber keine längeren gebeugten Formen.
- Verbesserungsideen, jeweils als eigene Änderung mit neuem Korpuslauf zu prüfen und
  nicht an diesem Korpus abzustimmen: einfache deutsche Endungen (-en, -n, -e, -s, -ern)
  vor der Teilwortsuche abtrennen; häufige Wörter wie „nicht“, „vor“, „ohne“, „beim“,
  „Datei“ als Stoppwörter prüfen; eine Mindestgüte, unter der keine Treffer geliefert
  werden.

## Grenzen dieses Versuchs

- 32 Einträge sind sehr wenig; in großen Datenbanken verschieben sich BM25-Werte, und der
  Beifang dürfte zunehmen.
- Ein Autor hat Einträge, Fragen und Kategorien geschrieben und dabei die Arbeitsweise
  der Suche gekannt. Ein unabhängiger Korpus aus echten Fehlern fehlt weiterhin.
- Jede Frage hat genau einen erwarteten Eintrag; Fragen mit mehreren gleich guten
  Antworten wurden nicht geprüft.
- Gemessen wurde die CLI. MCP und JSONL rufen dieselbe Kernfunktion auf, wurden hier
  aber nicht eigens durchlaufen.
