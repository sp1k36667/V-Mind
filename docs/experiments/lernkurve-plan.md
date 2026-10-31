# Versuchsplan: Lernkurve mit selbst gefundenen, geprüften Erfahrungen

Stand: Plan, noch nicht durchgeführt. Festgelegt vor dem ersten Lauf, damit Ziel,
Messgrößen und Erfolgskriterium nicht nachträglich an Ergebnisse angepasst werden.

## Frage

Wird ein kleines lokales Modell über eine Folge **ähnlicher, aber verschiedener**
Aufgaben besser und schneller, wenn es eigene Fehlerlösungen als kurze Erfahrungen
in V-Mind ablegt und diese erst nach einem bestandenen Test gelten?

Abgrenzung zum Pilot (`e2b-pilot.md`): Dort lag die vollständige Lösung eines
stärkeren Modells für **dieselbe** Aufgabe vor. Hier gibt es kein fremdes Wissen,
keine vollständigen Referenzdateien und keine Wiederholung derselben Aufgabe.

## Hypothesen

- **H1 (Lernkurve):** Mit Lernschleife steigt die Erfolgsquote im ersten Versuch
  über die Position in der Aufgabenfolge; ohne Gedächtnis bleibt sie etwa gleich.
- **H2 (Zeit):** Mit Lernschleife sinken Versuche und Modellzeit bis zur bestandenen
  Abnahme über die Position.
- **H3 (Prüfung zählt):** Ungeprüft übernommene Erfahrungen helfen weniger oder
  schaden, weil auch falsche Lehren gespeichert werden.

## Aufgabenfamilie

Sechs kleine Python-Programme nur mit der Standardbibliothek, jeweils als Klasse
mit JSON-Speicherung plus Kommandozeile. Die fachlichen Anforderungen unterscheiden
sich, die typischen Fallstricke wiederholen sich:

| Aufgabe | Eigenheit |
|---|---|
| Aufgabenplaner | erledigt/offen |
| Notizbuch | Schlagwörter, Suche |
| Einkaufsliste | Mengen > 0, Zusammenführen gleicher Artikel |
| Kontakte | E-Mail eindeutig |
| Lesezeichen | URL muss mit http(s):// beginnen |
| Zeiterfassung | Start/Stopp, keine überlappenden Einträge |

Gemeinsame Fallstricke, an denen E2B im Pilot gescheitert ist:

1. Persistenz nach Wiederöffnung am genau übergebenen Pfad
2. IDs steigen nach Löschen weiter, keine Wiederverwendung
3. leere oder reine Leerzeichen-Eingaben lösen `ValueError` aus
4. unbekannte IDs lösen `ValueError` aus
5. beschädigte JSON-Datei löst `ValueError` aus und wird **nicht** überschrieben
6. Änderungen werden sofort gespeichert
7. Kommandozeile endet bei Fehlern mit Exit-Code ≠ 0

Jede Aufgabe hat eine **unabhängige Abnahme** mit 7 gemeinsamen Prüfungen (je
Fallstrick eine, benannt nach Kategorie, z. B. `test_korruptes_json_bleibt_erhalten`)
und 2 bis 3 aufgabenspezifischen. Die Abnahmen werden vor dem ersten Lauf
geschrieben und eingefroren (Hash im Bericht). Das Modell sieht sie nie direkt, nur
die Fehlermeldungen fehlgeschlagener Prüfungen.

## Bedingungen

Alle Bedingungen nutzen dasselbe Modell, denselben Startprompt, dieselben Einstellungen
(Kontext 8.192, Temperatur 0, Ausgabe 2.400 Tokens), dieselbe Aufgabenbeschreibung,
höchstens drei Versuche pro Aufgabe und dasselbe Testfeedback. Unterschied ist nur der
Gedächtnisblock im Prompt und was nach einer Aufgabe gespeichert wird.

| | A: ohne Gedächtnis | B: Lernschleife | C: ungeprüft |
|---|---|---|---|
| Gedächtnisblock | leer | bis 3 validierte Erfahrungen | bis 3 Erfahrungen, egal welcher Status |
| Nach der Aufgabe | nichts | Lehre vorschlagen → Prüfbefehl → `check` | Lehre vorschlagen, ohne Prüfung nutzen |

### Lernschleife in B

1. Schlägt im Versuch n eine Prüfung fehl und besteht sie in Versuch n+1, fragt der
   Host das Modell nach einer **kurzen Lehre**: Problem und Lösung in Worten, höchstens
   400 Zeichen, **kein Quelltext** (Host weist Antworten mit Codeblöcken oder mehr als
   zwei Codezeilen ab).
2. Host speichert sie per `propose` (Status `pending`).
3. Host setzt per `check-set` als Prüfbefehl genau die Abnahmeprüfung, die vorher
   fehlschlug und jetzt besteht, im Ordner der gelösten Aufgabe, mit vollem
   Testnamen. Die Ausgabe muss „Ran 1 test“ und „OK“ enthalten.
4. `vmind check` validiert die Lehre nur, wenn diese Prüfung besteht.
5. Vor jeder neuen Aufgabe ruft der Host per `recall` mit der Aufgabenbeschreibung
   höchstens drei validierte Lehren ab.

Damit gilt eine Lehre erst, wenn ein echter Test sie bestätigt, und es wird nur
Erfahrung in Worten übertragen, kein Code einer anderen Aufgabe.

## Ablauf und Wiederholungen

- Jede Bedingung durchläuft die sechs Aufgaben in **drei festen Reihenfolgen**
  (vorher zufällig gezogen, im Bericht genannt), damit kein Effekt nur an einer
  bestimmten Aufgabe hängt.
- Jede Kombination läuft mit **zwei Seeds** (42 und 7). Pro Bedingung also
  6 Durchgänge × 6 Aufgaben = 36 Aufgabenläufe, insgesamt 108.
- Jeder Durchgang startet mit **leerer, eigener V-Mind-Datenbank**.
- Bedingungen abwechselnd ausführen (A, B, C, A, B, C …), um Wärme-/Cache-Effekte
  zu verteilen; Modell vor jedem Durchgang einmal mit einer Dummyanfrage laden.
- Geschätzte Laufzeit: etwa 1,5 Minuten pro Aufgabenlauf, insgesamt rund 3 Stunden.

## Messgrößen

Pro Aufgabenlauf, ausgewertet nach Position 1 bis 6 in der Folge:

- **Erfolg im ersten Versuch** (alle Abnahmeprüfungen bestanden), Hauptmessgröße
- bestandene Abnahmeprüfungen im ersten Versuch (Anteil)
- Versuche bis zum Bestehen (4 = nicht bestanden)
- Modellzeit bis zum Bestehen (Ollama-Dauerfelder), Ausgabe-Tokens
- welche Fallstrick-Kategorien fehlschlugen

Für B und C zusätzlich: vorgeschlagene, validierte und abgewiesene Lehren; welche
Lehren abgerufen wurden; ob die abgerufene Lehre zur danach bestandenen Kategorie passt.

## Erfolgskriterium (vorab festgelegt)

H1 gilt als gestützt, wenn in B die Erfolgsquote im ersten Versuch auf den Positionen
4 bis 6 mindestens **25 Prozentpunkte** über A liegt **und** dies in mindestens fünf
von sechs Durchgängen gleichgerichtet ist. H2 gilt als gestützt, wenn die mittlere
Modellzeit bis zum Bestehen auf Positionen 4 bis 6 in B kleiner ist als in A.
H3 wird beschreibend berichtet. Ergebnisse werden auch berichtet, wenn sie
dagegen sprechen.

## Grenzen, vorab benannt

- Kleine Stichprobe, eine Aufgabenfamilie, ein Modell; keine allgemeine Aussage.
- Abnahmen und Aufgaben stammen vom Versuchsleiter (Claude Code), nicht vom Modell.
- Temperatur 0 mit festen Seeds: Variation kommt vor allem aus Reihenfolgen.
- Auch ohne Gedächtnis lernt das Modell **innerhalb** einer Aufgabe aus Feedback;
  gemessen wird nur der Transfer **zwischen** Aufgaben.
- Die Lehren-Abfrage (FTS5) kann passende Lehren übersehen; das wird mitgemessen.

## Festlegungen beim Bau (vor dem ersten gezählten Lauf)

- Das Modell erzeugt nur `app.py`, keine eigene Testsuite; bewertet wird allein die
  unabhängige Abnahme mit 9 Prüfungen (7 gemeinsame, 2 aufgabenspezifische).
- Statt der 10.000 Zeichen langen Startanweisung (`prompts/start.de.md`) erhält das
  Modell in allen Bedingungen dieselbe kurze Systemanweisung, damit Aufgabe, Code,
  Rückmeldung und Antwort in 8.192 Tokens passen.
- **C** fragt nach jeder Aufgabe zu **jeder** Prüfung, die in irgendeinem Versuch
  fehlschlug, eine Lehre ab, auch wenn der Fehler nie behoben wurde, und übernimmt sie
  ohne Prüfung. **B** fragt nur zu Prüfungen, die zuerst fehlschlugen und am Ende
  bestehen, und validiert über `check` genau diese Prüfung. Höchstens 3 Lehren je Aufgabe.
- Lehren werden abgewiesen, wenn sie kein gültiges JSON sind, zu lang sind oder
  Quelltextmerkmale enthalten (Codeblöcke, `def`, `import`, `class`, `self.`, `return`).
- Abruf vor jeder Aufgabe: `recall` mit dem Aufgabentext (allgemeiner Teil zuerst),
  höchstens 3 Treffer. Rückmeldung bei Fehlschlag: Namen und Tracebacks der
  fehlgeschlagenen Prüfungen (höchstens 1.800 Zeichen) plus der vorherige Code.
- Reihenfolgen: mit festem Zufallsstartwert 20261031 gezogen (in `run.py`).
- Die Abnahmen sind per Selbsttest geprüft (`selbsttest.py`): Referenzlösungen bestehen
  9/9 in allen Aufgaben, sechs gezielt eingebaute Fehler werden in allen Aufgaben erkannt.

## Umsetzung

- Testhost: `examples/lernkurve/run.py` (baut auf `gemma_regeneration_test.py` auf),
  Aufgaben und Abnahmen unter `examples/lernkurve/aufgaben/`, alles im Repository.
- Versuchsdaten außerhalb des Repositorys: `/run/media/sp1k3/Code2/v-mind-lernkurve/`,
  je Durchgang eigener Ordner mit Datenbank, Prompts, Antworten und Testausgaben.
- Auswertung: `examples/lernkurve/auswerten.py` erzeugt Tabellen je Position und
  Bedingung; Bericht danach unter `docs/experiments/lernkurve.md`.
- Vorher ein **Probelauf** mit zwei Aufgaben je Bedingung, um den Host zu prüfen.
  Probelaufdaten fließen nicht in die Auswertung ein.
