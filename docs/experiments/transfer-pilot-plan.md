# Entwurf: Transfer-Pilot mit Gemma 4 12B

**Status: Entwurf zur Abstimmung zwischen Claude, Codex und dem Nutzer. Nicht freigegeben;
kein Lauf gestartet.** Nach Freigabe wird dieser Plan vor dem ersten gezählten Lauf
eingefroren (Commit-Hash im Bericht). Hintergrund: [lernkurve.md](lernkurve.md).

## Frage

Hilft eine einzelne, korrekte und geprüfte Erfahrung Gemma 4 12B bei einer **neuen**
Aufgabe, denselben Fehler zu vermeiden, ohne dort zu schaden, wo die Regel nicht gilt?

Die Lernkurven-Läufe konnten das nicht trennen: Lehren waren oft aufgabenspezifisch,
ein Fix bestätigte mehrere Lehren gleichzeitig, und die Suche bestimmte mit, was im
Prompt landete. Dieser Pilot misst einen Fehlertyp, ohne Suche, mit eigener Zielprüfung.

## Fehlertyp

„JSON-Objektschlüssel sind nach dem Laden Strings. Vor dem Rechnen mit numerischen IDs,
die als Schlüssel gespeichert sind, in Ganzzahlen umwandeln.“

Begründung: 12B machte diesen Fehler in mehreren Durchgängen und Aufgaben selbst
(Einkaufsliste, Aufgabenplaner), er ist eindeutig prüfbar, und es gibt einen echten
Gegenfall.

**Gegenfall:** Daten sind nach Namen geschlüsselt (z. B. Vorratsliste nach Artikelname).
Eine Umwandlung der Schlüssel in Ganzzahlen ist dort falsch und führt zum Absturz.

## Aufgaben

- 4 neue Transferaufgaben, die nicht im Lernkurvenexperiment vorkamen. Jede speichert
  Einträge als JSON-Objekt mit numerischen ID-Schlüsseln und verlangt nach dem Neuladen
  eine fortlaufende ID. Die Spezifikation nennt das Speicherformat, aber nicht die
  Falle.
- 1 Gegenfallaufgabe mit Namensschlüsseln.
- Je Aufgabe eine **Zielprüfung** (Neuladen, dann neuen Eintrag anlegen, ID korrekt) und
  die vorhandenen allgemeinen Prüfungen als Schadensmaß.
- Referenzlösungen und Mutations-Selbsttest wie bisher, bevor gezählt wird.

## Bedingungen

| Kürzel | Inhalt im Prompt |
|---|---|
| O | keine Erfahrung |
| L | die Erfahrung (Wortlaut oben, ohne Quelltext) |
| P | Placebo: wahre, gleich lange Erfahrung ohne Bezug (z. B. zu Zeitzonen) |

Die Erfahrung wird **direkt** in den Prompt gegeben, an derselben Stelle wie bisher
abgerufene Lehren. Keine Suche, damit Suchqualität keine Rolle spielt.

## Ablauf

0. **Vorlauf (Bedingung O allein, Machbarkeit):** 4 Aufgaben × 5 eigene Seeds
   (901 bis 905), nur erster Versuch. Weiter nur, wenn die Zielprüfung in **höchstens
   60 %** der Läufe besteht (sonst gibt es zu wenig zu verbessern; dann anderen
   Fehlertyp wählen). Die Grenze ist vorab eingefroren; bei Fehlschlag wird nicht auf
   denselben Seeds an Aufgaben oder Prompt nachgebessert. Der Vorlauf geht **nicht** in
   die Hauptauswertung ein, weil er nach seiner niedrigen Erfolgsquote ausgewählt wird
   (Selektionsverzerrung).
1. **Obergrenze:** O, L und P mit frischen Seeds 1001 bis 1010 auf denselben 4 Aufgaben,
   also 40 gepaarte Läufe je Bedingung (gleiche Aufgabe und gleicher Seed in O, L und P).
   Die Reihenfolge von O, L und P wird je Paar zufällig festgelegt (Startwert im
   eingefrorenen Plan). Die Erfahrung ist hier von Hand geschrieben und korrekt.
2. Nur wenn 1 das Erfolgskriterium erfüllt: **Erwerb.** 12B löst eine Quellaufgabe mit
   dieser Falle bis zum Bestehen; aus dem bereinigten Diff entsteht eine Erfahrung. Sie
   gilt nur, wenn
   a) eine vom Modellcode unabhängige Faktprüfung besteht (`json.loads(json.dumps({1: "a"}))`
      liefert Schlüssel vom Typ `str`) und
   b) die Rücknahme genau dieser Änderung die Zielprüfung wieder scheitern lässt.
3. **Transfer** mit der selbst erworbenen Erfahrung, gleicher Aufbau und gleiche
   Kriterien wie 1.

Gegenfall: 10 Seeds je Bedingung O, L, P.

Einstellungen: nur erster Versuch, Temperatur 0,7, Seeds wie oben (nie zuvor benutzt),
Modell vor jedem Lauf entladen wie bisher.

## Erfolgskriterium (vorab, für Schritt 1 und 3 gleich)

Zielprüfung bestanden im ersten Versuch, je 40 Läufe:

- L mindestens **30 Prozentpunkte** über O **und** einseitiger exakter McNemar-Test
  über die gepaarten Läufe L gegen O mit p < 0,05 (die Daten sind gepaart; ein
  Fisher-Test über die zusammengefassten Zahlen wird nur explorativ berichtet),
- L mindestens **20 Prozentpunkte** über P,
- in mindestens **3 von 4** Aufgaben L > O.

## Schadensgrenzen

- Anteil bestandener übriger Prüfungen unter L höchstens **10 Prozentpunkte** unter O.
- Gegenfall: Fehlanwendung (Abstürze oder falsche Ausgaben durch Umwandlung) unter L
  höchstens **1 von 10** häufiger als unter O.

Wird eine Schadensgrenze verletzt, gilt der Pilot als nicht bestanden, auch wenn das
Erfolgskriterium erfüllt ist. Umgekehrt ist das Einhalten der Gegenfallgrenze bei 10
Läufen nur beschreibend und **kein Nachweis**, dass die Erfahrung dort unschädlich ist.

## Trennschärfe

Simuliert mit exaktem einseitigem Fisher-Test, α = 0,05 (`examples/lernkurve/trennschaerfe.py`):

| Läufe je Bedingung | Basis 50 %, +30 pp | Basis 50 %, +40 pp | Basis 40 %, +30 pp |
|---:|---:|---:|---:|
| 20 | 0,53 | 0,84 | 0,46 |
| 30 | 0,71 | 0,95 | 0,67 |
| 40 | 0,84 | 0,99 | 0,80 |

Deshalb 40 Läufe je Bedingung. Mit 20 Läufen würde ein echter Effekt von 30 pp etwa
jedes zweite Mal übersehen. Beispiele bei 20 gegen 20: 12 gegen 6 ergibt p = 0,055,
14 gegen 6 ergibt p = 0,013. Die Tabelle gilt für unabhängige Gruppen; für den
gepaarten McNemar-Test wird die Trennschärfe vor dem Einfrieren getrennt simuliert.

Aufwand: Vorlauf 20, Schritt 1 3 × 40, Gegenfall 3 × 10, zusammen 170 Läufe mit je
einem Versuch.

## Grenzen

- Ein Fehlertyp zeigt höchstens, ob Transfer in einem sauberen Fall funktioniert, nicht,
  dass er allgemein funktioniert.
- Die Aufgaben stammen von uns; ein Bestehen belegt keine Wirkung auf fremde Projekte.
- Fällt Schritt 1 durch, ist das ein Ergebnis: Dann hilft schon eine korrekte Erfahrung
  im Prompt nicht, und die Frage nach selbst erworbenen Erfahrungen stellt sich so nicht.

## Offene Punkte zur Abstimmung

- Wortlaut der Erfahrung und des Placebos.
- Wer baut Aufgaben und Host (Vorschlag: Codex prüft, Claude baut, oder umgekehrt).
- Trennschärfe des gepaarten McNemar-Tests simulieren (braucht eine Annahme zur
  Korrelation zwischen O und L auf demselben Paar).
- Schritt 2 und 3 werden ein eigener Plan, nachdem Schritt 1 ausgewertet ist (mit
  Codex vereinbart).

Review: Codex (Teamkanal, Nachricht #20) – Vorlauf getrennt, Randomisierung, gepaarter
Test, Gegenfall nur beschreibend, kein Nachbessern auf denselben Seeds; eingearbeitet.
