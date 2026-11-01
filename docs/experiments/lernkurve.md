# Bericht: Lernkurve mit selbst gefundenen, geprüften Erfahrungen

Plan, Hypothesen, Erfolgskriterium und alle Änderungen vor dem ersten gezählten Lauf:
[lernkurve-plan.md](lernkurve-plan.md). Testhost: `examples/lernkurve/`.
Rohdaten (Prompts, Antworten, Abnahmeausgaben, Datenbanken) liegen lokal unter
`/run/media/sp1k3/Code2/v-mind-lernkurve/` und sind nicht Teil des Repositorys.

## Kurzfassung

**Hauptlauf mit Gemma 4 E2B (vorab geplant): Die Hypothesen werden nicht gestützt.**
E2B hat in keiner Bedingung und an keiner Position eine Aufgabe vollständig gelöst, auch
nicht mit fünf Versuchen. Das vorab festgelegte Erfolgskriterium ist nicht erfüllt.

Der Lauf zeigt trotzdem drei Dinge deutlich, die für V-Mind wichtig sind:

1. **Ungeprüftes Gedächtnis sammelt Falsches.** Unter C wurden 103 Lehren übernommen; in
   einer Zufallsstichprobe von 20 waren 4 eindeutig falsch, darunter wiederholt „nächste
   ID = größte ID plus eins, um Wiederverwendung zu verhindern“, was das Gegenteil bewirkt.
2. **Der Engpass war der Abruf, nicht die Speicherung.** B hatte 24 bestätigte Lehren,
   rief sie aber nur bei 17 bis 33 % der späteren Aufgaben überhaupt ab. Ohne Abruf erhielt
   B denselben Prompt wie A und lieferte reproduzierbar denselben Code.
3. **Die Bestätigung per Prüfbefehl hat eine Zuordnungslücke.** Behebt ein Versuch einen
   Syntaxfehler, „bestehen“ plötzlich viele Prüfungen gleichzeitig. Die Lehre beschreibt
   dann den Syntaxfehler, wird aber von einer fachfremden Prüfung bestätigt. So wurde
   auch eine falsche Lehre validiert.

**Explorativer Lauf mit Gemma 4 12B:** 12B behebt Fehler und findet seine Lehren wieder,
zeigt aber ebenfalls keine Lernkurve für die geprüfte Bedingung B. Ungeprüfte Lehren (C)
waren bei 12B kaum falsch, und C lag beim Anteil bestandener Prüfungen vorn. Das spricht
dafür, dass sich die heutige Prüfung (Zuordnung „Prüfung schlug vorher fehl, jetzt nicht
mehr“) vor allem bei schwachen Modellen auszahlt und für stärkere geschärft werden muss.
Details unten.

## Aufbau in Kürze

Sechs ähnliche Python-Aufgaben mit JSON-Speicherung und Kommandozeile, je 9 unabhängige
Prüfungen (7 gemeinsame Fallstricke, 2 aufgabenspezifische). Bedingungen: **A** ohne
Gedächtnis, **B** Lehren gelten erst nach bestandenem `vmind check` gegen die vorher
fehlgeschlagene Prüfung, **C** Lehren ohne Prüfung. 3 Reihenfolgen × 2 Seeds × 3
Bedingungen = 18 Durchgänge mit je 6 Aufgaben (108 Aufgabenläufe), jeder Durchgang mit
leerer Datenbank. Versuch 1 bei Temperatur 0 nach frisch geladenem Modell (reproduzierbar),
Wiederholungen bei 0,7, höchstens 5 Versuche. Lehren in Worten, ohne Quelltext, zu
behobenen Fehlern aus dem bereinigten Code-Diff.

## Ergebnisse E2B (Hauptlauf, vorab geplant)

Hauptmessgröße: Aufgabe im ersten Versuch vollständig bestanden. Zusätzlich der Anteil
bestandener Prüfungen im ersten Versuch und der Anteil der Aufgaben, bei denen überhaupt
Gedächtnis abgerufen wurde. Je Zeile 6 Aufgabenläufe.

| Pos. | Erfolg 1. V. A / B / C | Prüfungen 1. V. A | B | C | Gedächtnis B | C |
|---:|---|---:|---:|---:|---:|---:|
| 1 | 0 % / 0 % / 0 % | 41 % | 41 % | 41 % | 0 % | 0 % |
| 2 | 0 % / 0 % / 0 % | 37 % | 37 % | 52 % | 0 % | 67 % |
| 3 | 0 % / 0 % / 0 % | 44 % | 54 % | 50 % | 17 % | 100 % |
| 4 | 0 % / 0 % / 0 % | 26 % | 20 % | 41 % | 17 % | 100 % |
| 5 | 0 % / 0 % / 0 % | 41 % | 46 % | 39 % | 33 % | 100 % |
| 6 | 0 % / 0 % / 0 % | 33 % | 33 % | 31 % | 33 % | 100 % |

Keine Aufgabe wurde in irgendeinem Versuch vollständig bestanden (0 von 108). Damit ist
auch die Modellzeit bis zum Bestehen (H2) nicht bestimmbar.

Paarweiser Vergleich je Reihenfolge und Seed, Positionen 4 bis 6, Differenz des Anteils
bestandener Prüfungen im ersten Versuch zu A in Prozentpunkten:

| Reihenfolge, Seed | B − A | C − A |
|---|---:|---:|
| 1, 7 | 0 | +30 |
| 1, 42 | +11 | +44 |
| 2, 7 | 0 | +4 |
| 2, 42 | 0 | +4 |
| 3, 7 | 0 | −30 |
| 3, 42 | −11 | −30 |

- **H1 (Lernkurve): nicht gestützt.** Erfolg im ersten Versuch ist überall 0 %; das
  Kriterium „B mindestens 25 Prozentpunkte über A in mindestens 5 von 6 Durchgängen“ ist
  nicht erfüllt. Auch im Anteil bestandener Prüfungen gibt es keinen Anstieg über die
  Position.
- **H2 (Zeit): nicht bestimmbar**, da keine Aufgabe bestanden wurde.
- **H3 (Prüfung zählt), beschreibend:** C liegt auf den späten Positionen im Mittel
  um etwa 4 Prozentpunkte über A, mit Ausschlägen von −30 bis +44 je Durchgang, also ohne
  verlässliche Richtung. B unterscheidet sich kaum von A, weil B seine Lehren selten abrief.

## Lehren im Detail

| | B (geprüft) | C (ungeprüft) |
|---|---:|---:|
| vorgeschlagen | 24 | 105 |
| abgewiesen (Quelltext, Format) | 0 | 2 |
| übernommen | 24 | 103 |

**B, alle 24 von Hand eingeordnet:** 4 nützlich und übertragbar (z. B. „bei JSON-Fehlern
ValueError werfen, leere oder fehlende Datei als leere Daten behandeln“), 3
aufgabenspezifisch (Liste statt Dictionary), 15 trivial oder vage („try/except ergänzen,
um Syntaxfehler zu beheben“, „Klasse korrekt importieren“), 1 fragwürdig, 1 falsch
(„nächste ID ist max_id + 1“, bestätigt über eine Mengenprüfung, die mit IDs nichts zu tun
hat). Alle 24 stammen aus Seed 42; mit Seed 7 behob E2B keinen Fehler.

**C, Zufallsstichprobe von 20 der 91 verschiedenen Texte (Startwert 1):** 4 eindeutig
falsch („nächste ID = größte ID plus eins, um Wiederverwendung zu verhindern“, „ID nach
jedem Löschen neu berechnen“, „Host-Teil der URL muss numerisch sein“, „die Liste muss
ein Dictionary sein“), etwa 7 nützlich (z. B. „höchste vergebene ID nach dem Löschen
beibehalten“, „bei FileNotFoundError mit leeren Daten starten“, „unbekannte Befehle mit
Exitcode 1 beenden“), der Rest trivial, vage oder ohne Bezug zur Prüfung.

## Einordnung

Das Experiment hat die Kernidee nicht bestätigt, aber auch nicht widerlegt; es hat sie
unter den Bedingungen dieses Modells nicht greifen lassen. Die Gründe sind konkret:

- **Modellstärke.** E2B behebt Fehler selten selbst. Ohne behobene Fehler entstehen keine
  bestätigten Lehren; das war vorab als Risiko festgehalten.
- **Abruf.** Die reine Wortsuche (FTS5, ganze Wörter) fand die Lehren zu selten. Eine
  Teilwortsuche ist inzwischen umgesetzt (Schema 5), war in diesem Lauf aber nicht aktiv.
- **Zuordnung.** Die Bestätigung einer Lehre über „die Prüfung, die vorher fehlschlug und
  jetzt besteht“ ist zu grob, wenn ein einzelner Fix viele Prüfungen auf einmal umschaltet.

Was der Lauf stützt, ist die Grundannahme hinter V-Mind: **Ein Gedächtnis ohne Prüfung
übernimmt systematisch falsche Lehren**, und dieselbe falsche Lehre taucht in vielen
Durchgängen wieder auf.

## Nächste Schritte

1. Lehren nur aus Fixes ableiten, bei denen der vorherige Versuch nicht vollständig
   gescheitert war (kein Syntax- oder Importfehler, der alle Prüfungen umschaltet), und je
   Fix höchstens eine Lehre bilden.
2. Denselben Aufbau mit Teilwortsuche (Schema 5) wiederholen, um den Abrufengpass zu messen.
3. Aus dem 12B-Lauf: je Fix nur eine Lehre speichern (keine Vervielfachung je
   umgeschalteter Prüfung) und aufgabenspezifische Lehren (Klassen- und Methodennamen) nur
   im Bereich der Aufgabe ablegen, damit sie den Abruf für andere Aufgaben nicht füllen.
4. Mehr Aufgabenläufe je Zelle, damit Unterschiede wie C gegenüber A beim Prüfungsanteil
   von Zufall und Aufgabenreihenfolge trennbar werden.

## Explorativer Lauf mit Gemma 4 12B

**Explorativ**, nach dem E2B-Hauptlauf ergänzt (Plan: Commit c302f49). Gleicher Aufbau,
gleicher Code des Testhosts, nur `--modell gemma4:12b`. Die Ergebnisse sind nicht Teil der
vorab festgelegten Prüfung und dienen nur der Einordnung.

| Pos. | Erfolg 1. V. A / B / C | Prüfungen 1. V. A | B | C | bestanden A / B / C | Gedächtnis B | C |
|---:|---|---:|---:|---:|---|---:|---:|
| 1 | 0 % / 0 % / 0 % | 44 % | 44 % | 44 % | 0 % / 0 % / 0 % | 0 % | 0 % |
| 2 | 0 % / 0 % / 0 % | 56 % | 57 % | 57 % | 33 % / 17 % / 0 % | 67 % | 100 % |
| 3 | 0 % / 0 % / 0 % | 41 % | 43 % | 65 % | 0 % / 17 % / 0 % | 100 % | 100 % |
| 4 | 0 % / 17 % / 17 % | 67 % | 61 % | 74 % | 67 % / 33 % / 67 % | 100 % | 100 % |
| 5 | 0 % / 0 % / 0 % | 41 % | 35 % | 54 % | 0 % / 17 % / 17 % | 100 % | 100 % |
| 6 | 0 % / 0 % / 17 % | 41 % | 48 % | 57 % | 0 % / 17 % / 17 % | 100 % | 100 % |

„bestanden“ heißt: innerhalb von höchstens 5 Versuchen. Insgesamt bestand jede Bedingung
6 von 36 Aufgabenläufen.

Paarvergleich wie oben, Positionen 4 bis 6, Prozentpunkte zu A:

| Reihenfolge, Seed | B − A Erfolg | B − A Prüfungen | C − A Erfolg | C − A Prüfungen |
|---|---:|---:|---:|---:|
| 1, 7 | +33 | +26 | 0 | −4 |
| 1, 42 | 0 | −11 | 0 | +15 |
| 2, 7 | 0 | +4 | +33 | +7 |
| 2, 42 | 0 | −7 | 0 | +15 |
| 3, 7 | 0 | −26 | 0 | +7 |
| 3, 42 | 0 | +7 | +33 | +33 |

Beobachtungen:

- **Keine Lernkurve für B.** B liegt nur in einem von sechs Durchgängen beim Erfolg über A.
  Das Kriterium aus dem Plan (mindestens 25 Prozentpunkte in 5 von 6) wäre klar verfehlt.
- **C liegt beim Anteil bestandener Prüfungen vorn**: auf den späten Positionen im Mittel
  62 % gegenüber 50 % (A) und 48 % (B), in 5 von 6 Durchgängen über A. Bei 6 Aufgabenläufen
  je Zelle ist das ein Hinweis, kein Nachweis.
- **Was A löst, ist fast nur eine Aufgabe.** A bestand ausschließlich `lesezeichen`
  (6 von 6), B und C verteilen ihre Erfolge auf vier Aufgaben, bestehen `lesezeichen` aber
  seltener (3 bzw. 4 von 6). Die Positionsunterschiede in der Tabelle spiegeln deshalb
  stark wider, wo `lesezeichen` in der jeweiligen Reihenfolge steht.
- **Der Abruf funktioniert bei 12B.** Ab Position 3 rief B in allen Aufgaben Lehren ab
  (E2B: 17 bis 33 %), weil 12B mehr Fehler behob und daher mehr Lehren entstanden.
- **Die Zuordnungslücke zeigt sich als Vervielfachung.** Ein einzelner Fix erzeugt oft
  mehrere fast gleiche Lehren, eine je umgeschalteter Prüfung (z. B. dreimal
  „`list_items` in `list` umbenennen“).

Lehren:

| | B (geprüft) | C (ungeprüft) |
|---|---:|---:|
| vorgeschlagen und übernommen | 45 | 91 |
| verschiedene Texte | 37 | 77 |

**B, alle 45 von Hand eingeordnet:** 13 nützlich und übertragbar (fehlende Datei als leere
Daten behandeln; JSON-Schlüssel vor `max` in Ganzzahlen umwandeln; nächste ID dauerhaft
speichern), 6 richtig, aber allgemein (Fehler auf stderr, Exitcode ungleich 0), 18
aufgabenspezifisch (Klasse `NoteStore` anlegen, `list_items` in `list` umbenennen,
Argumentindizes), 5 vage, 2 fragwürdig („Mindestlänge der URL erhöhen“ als Ersatz für
eine echte Prüfung), 1 mit falscher Begründung („`total` überschreibt eine eingebaute
Funktion“; eine solche gibt es nicht).

**C, Zufallsstichprobe von 20 der 77 verschiedenen Texte (Startwert 1):** etwa 7 nützlich
(darunter richtig „nächste ID nicht aus dem Maximum berechnen, sonst werden gelöschte IDs
wiederverwendet“, also das Gegenteil des häufigsten E2B-Fehlers), 4 aufgabenspezifisch,
7 vage, 2 fragwürdig, **keine eindeutig falsch**.

Einordnung: Mit dem stärkeren Modell entfällt der Effekt, der bei E2B für die Prüfung
sprach. 12B schreibt auch ungeprüft kaum falsche Lehren, und die Prüfung filtert dann
wenig heraus. Sie lässt aber weiterhin Fragwürdiges und falsch Begründetes durch, weil
sie nur zeigt, dass der Code nach dem Fix eine Prüfung besteht, nicht, dass der Text der
Lehre stimmt. Dass C hier beim Prüfungsanteil vorn liegt, kann an der größeren Menge an
Lehren liegen; mit dieser Stichprobe lässt sich das nicht trennen.
