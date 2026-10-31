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

Der explorative Lauf mit Gemma 4 12B läuft noch; sein Ergebnis wird unten ergänzt.

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
3. Ergebnis des 12B-Laufs abwarten: Greift die Schleife, wenn das Modell Fehler beheben kann?

## Explorativer Lauf mit Gemma 4 12B

Läuft. Ergebnisse werden hier ergänzt und getrennt vom Hauptlauf ausgewiesen.
