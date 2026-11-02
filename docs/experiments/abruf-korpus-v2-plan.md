# Abrufkorpus v2: Plan für deutsche Wortformen und weniger Beifang

Festgelegt am 1. November 2026, **bevor** der Suchcode geändert und bevor eine
v2-Frage gestellt wurde. Korpus: [`examples/retrieval/corpus-v2.json`](../../examples/retrieval/corpus-v2.json).
Vorgänger: [Abrufkorpus v1](abruf-korpus.md).

## Anlass

v1 zeigte zwei Schwächen von `recall`: Längere gebeugte Formen in der Frage
(„Rundungsfehlern“) finden die kürzere gespeicherte Form nicht, und häufige Wörter
(„nicht“, „vor“, „Datei“) liefern beliebige Treffer, im Mittel 2,6 unpassende je
Frage mit erwartetem Eintrag.

## Geplante Änderung (Richtung, nicht an v1 abgestimmt)

1. **Wortstämme für die Teilwortsuche:** Von jedem Suchwort mit mindestens fünf Zeichen
   wird höchstens eine häufige deutsche Endung abgetrennt (`ern`, `en`, `er`, `es`, `e`,
   `n`, `s`, längste zuerst), sofern mindestens vier Zeichen übrig bleiben. Die
   Teilwortsuche verwendet diesen Stamm. Die Wortsuche (FTS5) bleibt unverändert.
2. **Mehr Füllwörter:** Häufige deutsche und englische Funktionswörter, darunter
   Verneinungen wie „nicht“ und „not“, zählen nicht als Suchwort. Eine Wortsuche kann
   Verneinung ohnehin nicht auswerten; die Inhaltswörter der Frage bleiben erhalten.
3. **Mindestabdeckung:** Ein Treffer muss mindestens halb so viele der Suchwörter
   (bzw. ihrer Stämme) enthalten wie der beste Treffer; mindestens eines.

Rangfolge innerhalb der Treffer, Limit 5, Bereichs-, Status- und Rückzugsfilter bleiben
unverändert. Keine Schemaänderung.

**Vorab bekannte Grenzen dieses Verfahrens:** Umlaut-Plurale („Passwörter“ → „Passwort“)
und unregelmäßige Formen („Indizes“ → „Index“) werden voraussichtlich nicht erkannt;
v04 und v05 sind deshalb als wahrscheinliche Fehlschläge markiert. Der Autor kannte die
geplante Richtung beim Schreiben von v2. Die Kategorie `getrennt` soll gerade die Fälle
treffen, in denen ein abgeschnittener Stamm zu ähnliche Wörter verbindet
(„Rechnern“ → „Rechn“ steckt in „Rechner“ und „Rechnung“).

## Korpus v2

28 neue Einträge (Bereiche `gamma`, `delta`, `global`; einer ungeprüft, einer
zurückgezogen) und 37 Fragen. Wortformfragen enthalten nur das gebeugte Wort bzw. Wörter
ohne andere Gemeinsamkeit mit dem Eintrag.

| Kategorie | Fragen | Prüft |
|---|---:|---|
| `wortform_lang` | 10 | Frage enthält die längere gebeugte Form |
| `wortform_kurz` | 4 | Frage enthält die kürzere Form (funktionierte schon in v1) |
| `getrennt` | 7 | ähnliche Wörter, die nicht verwechselt werden dürfen |
| `englisch` | 4 | englische Fehlermeldungen mit Funktionswörtern |
| `negation` | 2 | Fragen mit „nicht“ finden weiter den passenden Eintrag |
| `kein_treffer` | 6 | kein passender Eintrag, häufige Wörter in der Frage |
| `bereich`, `status` | 4 | Grenzen wie in v1 |

## Ablauf

1. **Basislauf:** v1 und v2 mit unverändertem main (`08a8024`), je zweimal mit frischer
   Datenbank, beide Rohlisten gespeichert.
2. Suchänderung mit Rust-Tests umsetzen.
3. **Neuer Lauf:** v1 und v2 mit dem geänderten Programm, gleiche Weise.
4. Korpus, Kriterien und Kategorien werden danach nicht geändert. Verfehlte Kriterien
   werden berichtet, nicht umgedeutet.

## Harte Kriterien (beide Korpora, beide Programme)

Keine Bereichs-, Status- oder Verbotslecks; zwei Läufe je Programm identisch.

## Erfolgskriterien der Änderung (alle müssen gelten)

| | Kriterium |
|---|---|
| K1 | v2 `wortform_lang`: Treffer@5 neu mindestens 8 von 10 |
| K2 | v2 `getrennt`: Treffer@1 neu mindestens 6 von 7 |
| K3 | v2 `wortform_kurz`, `englisch`, `negation`, Positivfall `bereich`: keine Frage verliert Treffer@1 gegenüber dem Basislauf |
| K4 | v2: mittlere Zahl unpassender Treffer je Frage mit erwartetem Eintrag neu kleiner als im Basislauf |
| K5 | v2 `kein_treffer`: mittlere Trefferzahl neu nicht größer als im Basislauf |
| R1 | v1 `wortgleich` Treffer@1 10/10 und `ablenker` Treffer@1 6/6 bleiben |
| R2 | v1: keine Frage, deren erwarteter Eintrag im Basislauf unter den Treffern war, verliert ihn |
| R3 | v1: mittlere Zahl unpassender Treffer je Frage mit erwartetem Eintrag nicht größer als im Basislauf |

Verfehlt die Änderung ein Kriterium, wird sie nicht als Verbesserung dargestellt.
Auch bei Erfolg bleibt es ein synthetischer Korpus eines Autors, der das Verfahren
kannte; ein Nutzennachweis für echte Projekte ist das nicht.
