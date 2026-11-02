# Plan: Transfer-Pilot mit Gemma 4 12B

**Status: vorbereitet, nicht eingefroren, kein Modelllauf.** Aufgaben, Prüfungen, Host,
Auswertung und Selbsttests liegen in [`examples/transfer/`](../../examples/transfer/).
Vor dem ersten gezählten Lauf prüft Codex Plan und Host unabhängig; danach wird der
Commit eingefroren und im Bericht genannt. Offene Entscheidungen stehen am Ende; solange
sie offen sind, gibt es keinen gezählten Lauf. Hintergrund: [lernkurve.md](lernkurve.md).

## Frage

Hilft eine einzelne, korrekte und geprüfte Erfahrung Gemma 4 12B bei einer **neuen**
Aufgabe, denselben Fehler zu vermeiden, ohne dort zu schaden, wo die Regel nicht gilt?

Die Lernkurven-Läufe konnten das nicht trennen: Lehren waren oft aufgabenspezifisch,
ein Fix bestätigte mehrere Lehren gleichzeitig, und die Suche bestimmte mit, was im
Prompt landete. Dieser Pilot misst einen Fehlertyp, ohne Suche, mit eigener Zielprüfung.

## Fehlertyp

JSON-Objektschlüssel sind nach dem Laden Strings. Wer Einträge unter numerischen IDs als
Schlüssel speichert, muss sie beim Laden in Ganzzahlen umwandeln. 12B machte diesen
Fehler in der Lernkurve selbst (Einkaufsliste, Aufgabenplaner); er ist eindeutig prüfbar,
und es gibt einen echten Gegenfall: Schlüssel, die Namen sind.

## Modell und Einstellungen

- `hf.co/google/gemma-4-12B-it-qat-q4_0-gguf:Q4_0`, Digest
  `18a4d9511d9965d973356e62310a2793771c22456be408cc06a05f04a6376acd` (lokal installiert,
  derselbe Digest wie in den Fortsetzungsläufen). Der Host bricht ab, wenn Name oder
  Digest abweichen. Kein E2B, kein Download, keine Änderung an ROCm.
- Nur erster Versuch, Temperatur 0,7, `num_ctx` 8192, `num_predict` 2400, `think: false`,
  Modell vor jedem Lauf entladen. Alle Werte in `bedingungen.json`, nicht per Argument
  änderbar.

## Aufgaben

Vier neue Transferaufgaben, die in der Lernkurve nicht vorkamen: `ausgaben`, `leihliste`,
`rezepte`, `termine`. Die allgemeine Anforderung schreibt das Speicherformat vor:
`{"next_id": …, "items": {"<ID>": {…}}}`, IDs als `int`. Die Falle selbst wird nicht
genannt. Gegenfall `vorrat`: Format `{"items": {"<Name>": Menge}}`.

Je Aufgabe:

- **Zielprüfung** (`test_ziel_ids_nach_neuladen`): elf Einträge anlegen, Datei hat das
  vorgeschriebene Format, nach dem Neuladen sind die IDs `int`, Ändern und Löschen per
  `int`-ID wirken, die nächste ID stimmt. Eine Formatverletzung (etwa Liste statt Objekt)
  umgeht die Falle und zählt deshalb als nicht bestanden; die Fehlermeldung beginnt dann
  mit „Format“ und wird getrennt berichtet.
- **Übrige Prüfungen** (Schadensmaß, je 7): leere Eingabe, unbekannte ID, beschädigte
  Datei bleibt erhalten, CLI-Exitcode, IDs steigen in einer Instanz, Texte nach Neuladen
  (ohne ID-Vergleich) und eine aufgabenspezifische Prüfung. Sie hängen bewusst nicht von
  der Schlüsselbehandlung ab.
- Gegenfall: Zielprüfung `test_ziel_namen_nach_neuladen` plus 5 übrige Prüfungen.

`selbsttest.py` belegt ohne Modell: Referenzen bestehen alles; eine Referenz **ohne**
Schlüsselumwandlung scheitert nur an der Zielprüfung und besteht alle übrigen; eine
Gegenfall-Referenz **mit** Umwandlung scheitert an der Zielprüfung; sechs allgemeine
Mutationen werden erkannt. Eine absichtlich entschärfte Zielprüfung lässt den Selbsttest
scheitern (geprüft).

## Bedingungen

| Kürzel | `gedaechtnis` im Prompt |
|---|---|
| O | leer |
| L | Problem: „JSON-Objektschlüssel sind nach dem Laden immer Strings; als Schlüssel gespeicherte numerische IDs kommen als Text zurück.“ Lösung: „Beim Laden solche Schlüssel in Ganzzahlen umwandeln, bevor mit den IDs verglichen, gesucht oder gerechnet wird.“ |
| P | Problem: „Zeitstempel ohne Zeitzone sind mehrdeutig; lokale Uhrzeiten springen bei der Umstellung auf die Sommerzeit und zurück.“ Lösung: „Zeitpunkte mit Zeitzone in UTC speichern und erst bei der Anzeige in die lokale Zeit umrechnen, niemals umgekehrt.“ |

L und P sind genau gleich lang (232 Zeichen). Die Prompts der drei Bedingungen
unterscheiden sich nur im Feld `gedaechtnis` (getestet). Die Erfahrung steht direkt im
Prompt, ohne Suche.

## Ablauf

0. **Vorlauf** (nur O, Machbarkeit): 4 Aufgaben × Seeds 901–905 = 20 Läufe. Weiter nur,
   wenn die Zielprüfung in **höchstens 12 von 20** (60 %) besteht **und** höchstens 2
   Läufe technisch ausfallen (HTTP-Fehler oder abgeschnittene Antwort). Bei zu vielen
   technischen Ausfällen wird der Host repariert und der Vorlauf einmal mit neuen Seeds
   911–915 wiederholt; bei zu hoher Erfolgsquote wird ein anderer Fehlertyp gewählt. Nie
   wird auf denselben Seeds nachgebessert. Der Vorlauf geht nicht in die Hauptauswertung
   ein (Selektionsverzerrung).
1. **Hauptlauf**: O, L, P mit Seeds 1001–1010 auf den 4 Aufgaben = 40 Paare, 120 Läufe.
   Reihenfolge der Paare und der Bedingungen je Paar zufällig, festgelegt durch
   `reihenfolge_seed` 20261102 (wiederholbar, getestet).
2. **Gegenfall**: `vorrat`, O, L, P mit Seeds 1101–1110 = 30 Läufe.
3. Erwerb und Transfer einer selbst erworbenen Erfahrung werden ein eigener Plan, erst
   nach Auswertung von 1 (mit Codex vereinbart).

Insgesamt 170 Modellaufrufe mit je einem Versuch.

**Durchführung:** Gezählte Läufe nur an einem Commit ohne uneingecheckte Änderungen in
`examples/transfer` (der Host prüft das). Abgeschlossene Läufe werden nie wiederholt; ein
unvollständiger Laufordner stoppt den Host zur Prüfung. Technische Fehler und
abgeschnittene Antworten zählen als nicht bestanden und werden getrennt berichtet;
liegen sie in einer Stufe über 10 %, gilt die Stufe als technisch gescheitert.

**Ausführung des Modellcodes:** ohne Shell, mit Zeitlimit 90 s je Abnahme und 20 s je
CLI-Aufruf, Ausgabe auf 200 kB begrenzt, `HOME` auf den Laufordner gesetzt. Das ist
**keine Sandbox**: Der Code läuft mit den Rechten des Nutzers. Rohdaten je Lauf: Anfrage,
Antwort, `app.py`, Abnahmeausgabe, `ergebnis.json`; sie gehören nicht ins Repository.

## Erfolgskriterium (vorab)

Zielprüfung bestanden im ersten Versuch, 40 Paare:

- L mindestens **X Prozentpunkte** über O (X siehe Entscheidung E1) **und** einseitiger
  exakter McNemar-Test über die Paare L gegen O mit p < 0,05,
- L mindestens **20 Prozentpunkte** über P,
- in mindestens **3 von 4** Aufgaben L > O.

## Schadensgrenzen

- Anteil bestandener übriger Prüfungen unter L höchstens **10 Prozentpunkte** unter O.
- Gegenfall: Fehlschläge der Zielprüfung unter L höchstens **1 von 10** häufiger als
  unter O. Die Ursache jedes Fehlschlags wird im Rohcode geprüft (Umwandlung oder anderes).

Wird eine Schadensgrenze verletzt, gilt der Pilot als nicht bestanden. Das Einhalten der
Gegenfallgrenze bei 10 Läufen ist nur beschreibend und **kein Nachweis** der
Unschädlichkeit.

## Trennschärfe (gepaart, simuliert)

`trennschaerfe_gepaart.py`: 40 Paare, gemeinsame Schwierigkeit je Paar über eine
Gauß-Copula mit Korrelation ρ, 20 000 Simulationen. Werte: nur McNemar / McNemar **und**
beobachteter Abstand ≥ 30 pp.

| Basis O | wahres L | ρ = 0 | ρ = 0,3 | ρ = 0,6 |
|---:|---:|---:|---:|---:|
| 50 % | 80 % | 0,84 / 0,55 | 0,90 / 0,56 | 0,95 / 0,55 |
| 50 % | 90 % | 0,99 / 0,89 | 1,00 / 0,90 | 1,00 / 0,92 |
| 40 % | 70 % | 0,81 / 0,56 | 0,88 / 0,56 | 0,94 / 0,56 |
| 30 % | 60 % | 0,81 / 0,55 | 0,88 / 0,55 | 0,94 / 0,56 |
| 50 % | 50 % | 0,03 / 0,00 | 0,03 / 0,00 | 0,03 / 0,00 |

Liegt die Abstandsschwelle genau beim wahren Effekt (30 pp), besteht das Kriterium nur
etwa jedes zweite Mal. Mit Schwelle 20 pp (Probe mit 10 000 Simulationen): 50 % → 80 %
ergibt 0,84 bei ρ = 0 und 0,88 bei ρ = 0,3; ohne Effekt bleibt die Fehlerrate bei 0,03.
Die Simulation nimmt unabhängige Paare an; tatsächlich sind sie über vier Aufgaben
geclustert, deshalb ist sie eher zu optimistisch, und die Regel „3 von 4 Aufgaben“ bleibt
nötig. P und die Aufgabenregel senken die Trennschärfe weiter.

## Grenzen

- Ein Fehlertyp zeigt höchstens, ob Transfer in einem sauberen Fall funktioniert, nicht,
  dass er allgemein funktioniert. Kein Lernnachweis über diese Aufgaben hinaus.
- Die Aufgaben stammen von uns; ein Bestehen belegt keine Wirkung auf fremde Projekte.
- Die Erfahrung ist von Hand geschrieben und korrekt; ob 12B eine gleich gute selbst
  erwirbt, prüft erst der spätere Plan.
- Fällt der Hauptlauf durch, ist das ein Ergebnis: Dann hilft schon eine korrekte
  Erfahrung im Prompt nicht.

## Offene Entscheidungen vor dem Einfrieren

- **E1 Abstandsschwelle:** 30 pp (Original; ≈ 0,55 Trennschärfe bei wahrem Effekt
  30 pp, ≈ 0,9 bei 40 pp) oder 20 pp (≈ 0,85 bei 30 pp, Fehlerrate unverändert)?
  Vorschlag Claude: 20 pp als Mindestabstand, 30 pp als vorab genannter erwarteter
  Effekt, beide im Bericht.
- **E2 Prüfung durch Codex:** Aufgabenwortlaut (verrät die allgemeine Anforderung die
  Falle zu stark?), Zielprüfung inklusive Format, Erfahrungs- und Placebotext, Host.
- **E3 Freeze:** Commit nach Einarbeitung der Prüfung; der Hash steht im Bericht.

Review: Codex (Teamkanal #20, #165) – Vorlauf getrennt, Randomisierung, gepaarter Test,
Gegenfall nur beschreibend, kein Nachbessern auf denselben Seeds; eingearbeitet.
