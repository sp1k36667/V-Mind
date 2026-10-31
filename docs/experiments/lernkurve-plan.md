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
(Kontext 8.192, Ausgabe 2.400 Tokens; Versuch 1 mit Temperatur 0, Wiederholungen mit
0,7), dieselbe Aufgabenbeschreibung, höchstens fünf Versuche pro Aufgabe und dasselbe
Testfeedback. Unterschied ist nur der
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
- Versuche bis zum Bestehen (6 = nicht bestanden)
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

## Probelauf 1 und daraus folgende Änderung

Probelauf mit A, B und C, zwei Aufgaben (Aufgabenplaner, Kontakte), Seed 42, höchstens
drei Versuche, alles bei Temperatur 0. Zählt nicht zur Auswertung.

- Der Host arbeitete korrekt: Fehler waren echte Modellfehler (z. B. nach dem Laden aus
  JSON Text- statt Zahl-IDs, Kommandozeile lehnt noch nicht vorhandene Datei ab), die
  Rückmeldung kam an (Prompt ab Versuch 2 rund 2.900 statt 500 Tokens).
- E2B behob in keinem Fall einen Fehler; beim Aufgabenplaner waren Versuch 2 und 3
  bytegleich. Dadurch entstand unter B keine einzige bestätigte Lehre, B war nicht
  von A zu unterscheiden.
- Unter C wurden sechs Lehren übernommen, darunter nachweislich falsche: „Existenz der
  Datei vor dem Instanziieren prüfen“ ist genau der gemachte Fehler, „nächste ID =
  maximale ID + 1, um Wiederverwendung zu verhindern“ bewirkt das Gegenteil, eine Lehre
  passte nicht zu ihrer Prüfung. Einzelbeobachtung, kein Ergebnis.

Änderung vor dem ersten gezählten Lauf, für alle Bedingungen gleich: Versuch 1 bleibt bei
Temperatur 0 (Hauptmessgröße unverändert); Wiederholungen nutzen Temperatur 0,7 mit
eigenem Seed (Seed + Versuchsnummer − 1); höchstens fünf statt drei Versuche.

Bekannte Schwäche von B, die sich im Probelauf zeigte: Der Prüfbefehl bestätigt, dass der
**Code** die Prüfung besteht, nicht, dass die **Formulierung** der Lehre stimmt. Eine
falsch formulierte Lehre zu einem behobenen Fehler würde validiert. Das wird bei der
Auswertung je Lehre von Hand nachgesehen und berichtet.

## Probelauf 2 und daraus folgende Änderung

Wie Probelauf 1, aber mit Streuung bei Wiederholungen und bis zu fünf Versuchen. Zählt
nicht zur Auswertung. Der Code unterschied sich nun von Versuch zu Versuch, trotzdem
scheiterten immer dieselben Prüfungen; B erhielt erneut keine Lehre.

Ursache lag im Host: Die Rückmeldung wurde von hinten auf 1.800 Zeichen gekürzt. Dadurch
fiel die Liste der fehlgeschlagenen Prüfungen weg, und der Platz ging für lange absolute
Pfade und wiederholte Traceback-Zeilen verloren; die auslösende Eingabe (z. B. eine
gültige E-Mail, die abgelehnt wurde) war oft nicht zu sehen.

Änderung vor dem ersten gezählten Lauf, für alle Bedingungen gleich: Rückmeldung beginnt
immer mit der Liste der fehlgeschlagenen Prüfungen; je Prüfung folgen der aufrufende
Prüfschritt und die Stellen in `app.py` mit der Fehlerzeile, ohne absolute Pfade, je
höchstens 450 Zeichen, insgesamt höchstens 2.500 Zeichen. An den Daten von Probelauf 2
offline geprüft (Aufgabenplaner rund 700, Kontakte rund 1.600 Zeichen).

## Probelauf 3

Wie Probelauf 2, mit kompakter Rückmeldung. Zählt nicht zur Auswertung.

- Erstmals behob E2B Fehler selbst: unter B bei den Kontakten 3/9 → 6/9 (Versuch 4).
  Daraus entstanden drei Lehren, alle drei über `vmind check` von genau der vorher
  fehlgeschlagenen Prüfung bestätigt. Die Lernschleife lief damit erstmals vollständig.
- Die Lehren trafen den eigentlichen Fix nicht: Behoben wurde eine zu strenge
  E-Mail-Prüfung, die Lehren lauteten etwa „Validierungsergebnisse müssen explizit in die
  Fehlermeldung integriert werden“. Damit ist die vorab benannte Schwäche belegt: Der
  Prüfbefehl bestätigt den Code, nicht die Formulierung.
- Unter C wurden erneut falsche Lehren übernommen, z. B. „`str()` verwenden, um die ID
  zu einem String hinzuzufügen“ (richtig wäre, IDs nach dem Laden als Zahl zu behandeln).
- Beim Aufgabenplaner behob E2B in keiner Bedingung einen Fehler, auch nicht in fünf
  Versuchen.

Offene Entscheidung vor dem Hauptlauf: Die Lehre sollte aus dem **Unterschied** zwischen
fehlgeschlagenem und bestandenem Code formuliert werden, nicht nur aus Fehlermeldung und
Endstand. Erst dann misst B, ob übertragene Erfahrung hilft, und nicht, ob vage
Allgemeinplätze helfen.

## Änderung nach Probelauf 3: Lehren aus dem Code-Unterschied

Vor dem ersten gezählten Lauf, für B und C gleich: Zu jedem **behobenen** Fehler erhält
das Modell beim Formulieren der Lehre den Unterschied (unified diff, nur Inhaltszeilen
ohne Leerzeilen und reine Kommentare, höchstens 3.000 Zeichen) zwischen dem letzten
fehlgeschlagenen und dem ersten danach bestandenen Code, dazu die Fehlermeldung genau
dieses fehlgeschlagenen Versuchs. C erhält zu nie behobenen Fehlern weiterhin die
Fehlermeldung und den letzten Code, ohne Diff.

Offline an den Daten von Probelauf 3 (B, Kontakte) geprüft: Der bereinigte Diff zeigt
den eigentlichen Fix (eine Prüffunktion, die Ausnahmen wirft und nichts zurückgibt, war
mit `if not …` abgefragt worden, wodurch jede E-Mail abgelehnt wurde). Von drei Lehren
beschrieb eine den Fix annähernd („Validierungsfehler abfangen und weitergeben“), zwei
eine nebensächliche JSON-Änderung im selben Diff. Das ist eine Grenze des Modells beim
Lesen von Diffs und wird bei der Auswertung je Lehre berichtet.

## Probelauf 4 und Determinismus

Diff-Lehren, drei Aufgaben (Kontakte, Lesezeichen, Aufgabenplaner), Seed 42. Zählt nicht
zur Auswertung.

- Abruf und Übertragung funktionieren technisch: B rief bei Lesezeichen und Aufgabenplaner
  die drei Lehren aus den Kontakten ab.
- B lernte beim Aufgabenplaner per Prüfbefehl bestätigt „Schlüssel vor der Prüfung in
  Integer umwandeln“, genau den Fehler, an dem E2B dort in allen Probeläufen scheiterte
  (IDs sind nach dem Laden aus JSON Text).
- C übernahm erneut Falsches, z. B. „Nach Löschung müssen alle IDs neu nummeriert werden,
  um Wiederverwendung zu verhindern“, das Gegenteil der Anforderung.
- **Nicht deterministisch:** Bei der ersten Aufgabe waren Prompt, Systemanweisung und
  Einstellungen in A, B und C byte-gleich (Temperatur 0, Seed 42), C erhielt trotzdem eine
  andere Antwort (6/9 statt 3/9). Gegentest mit derselben Anfrage: dreimal hintereinander
  gleich, aber anders als das Original; nach Entladen des Modells war die erste Antwort
  wieder gleich dem Original, die zweite schon nicht mehr. Die Antwort hängt also vom
  Zwischenspeicherzustand des Modells ab.

Änderung vor dem ersten gezählten Lauf, für alle Bedingungen gleich: Vor dem ersten
Versuch jeder Aufgabe wird das Modell entladen (`keep_alive: 0`), damit die Hauptmessgröße
reproduzierbar ist. Ladezeit wird getrennt erfasst (`lade_ms`) und nicht zur Modellzeit
gezählt. Für Wiederholungen mit Temperatur 0,7 ist Streuung ohnehin gewollt.

## Probelauf 5: Kontrolle der Reproduzierbarkeit

Kontakte und Lesezeichen, A/B/C, Seed 42, Modell vor jedem ersten Versuch entladen.
Zählt nicht zur Auswertung.

- Kontakte, Versuch 1: in A, B und C byte-gleicher Code, identisch mit A aus Probelauf 4.
  Lesezeichen, Versuch 1: A und B byte-gleich (B hatte keine Lehre), C abweichend wegen
  anderer Eingabe (ungeprüfte Lehren). Die Hauptmessgröße ist damit reproduzierbar.
- Bei reproduzierbarem Verhalten behob E2B bei den Kontakten in fünf Versuchen keinen
  Fehler; der Fix aus Probelauf 4 war vom Zwischenspeicherzustand abhängig. B erhielt
  daher keine Lehre.

Erwartung vor dem Hauptlauf, offen festgehalten: Weil E2B Fehler selten selbst behebt,
wird B wenige Lehren erhalten. Ein Ergebnis „kein Unterschied zwischen A und B“ würde
dann vor allem zeigen, dass dieses Modell für Selbstlernen über Fehlerbehebung zu schwach
ist, nicht dass geprüfte Lehren nutzlos sind. Die Zahl der behobenen Fehler und der
validierten Lehren wird deshalb im Bericht an erster Stelle genannt.

## Umsetzung

- Testhost: `examples/lernkurve/run.py` (baut auf `gemma_regeneration_test.py` auf),
  Aufgaben und Abnahmen unter `examples/lernkurve/aufgaben/`, alles im Repository.
- Versuchsdaten außerhalb des Repositorys: `/run/media/sp1k3/Code2/v-mind-lernkurve/`,
  je Durchgang eigener Ordner mit Datenbank, Prompts, Antworten und Testausgaben.
- Auswertung: `examples/lernkurve/auswerten.py` erzeugt Tabellen je Position und
  Bedingung; Bericht danach unter `docs/experiments/lernkurve.md`.
- Vorher ein **Probelauf** mit zwei Aufgaben je Bedingung, um den Host zu prüfen.
  Probelaufdaten fließen nicht in die Auswertung ein.
