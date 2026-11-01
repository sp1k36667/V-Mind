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

0. **Vorlauf (Bedingung O allein):** 4 Aufgaben × 10 frische Seeds, nur erster Versuch.
   Weiter nur, wenn die Zielprüfung in **höchstens 60 %** der Läufe besteht (sonst gibt
   es zu wenig zu verbessern; dann anderen Fehlertyp wählen). Der Vorlauf zählt als O.
1. **Obergrenze:** L und P mit denselben 40 Läufen (Aufgaben × Seeds) wie O. Die
   Erfahrung ist hier von Hand geschrieben und korrekt.
2. Nur wenn 1 das Erfolgskriterium erfüllt: **Erwerb.** 12B löst eine Quellaufgabe mit
   dieser Falle bis zum Bestehen; aus dem bereinigten Diff entsteht eine Erfahrung. Sie
   gilt nur, wenn
   a) eine vom Modellcode unabhängige Faktprüfung besteht (`json.loads(json.dumps({1: "a"}))`
      liefert Schlüssel vom Typ `str`) und
   b) die Rücknahme genau dieser Änderung die Zielprüfung wieder scheitern lässt.
3. **Transfer** mit der selbst erworbenen Erfahrung, gleicher Aufbau und gleiche
   Kriterien wie 1.

Gegenfall: 10 Seeds je Bedingung O, L, P.

Einstellungen: nur erster Versuch, Temperatur 0,7, Seeds 1001 bis 1010 (nie zuvor
benutzt), Modell vor jedem Lauf entladen wie bisher.

## Erfolgskriterium (vorab, für Schritt 1 und 3 gleich)

Zielprüfung bestanden im ersten Versuch, je 40 Läufe:

- L mindestens **30 Prozentpunkte** über O **und** einseitiger exakter Fisher-Test
  L gegen O mit p < 0,05,
- L mindestens **20 Prozentpunkte** über P,
- in mindestens **3 von 4** Aufgaben L > O.

## Schadensgrenzen

- Anteil bestandener übriger Prüfungen unter L höchstens **10 Prozentpunkte** unter O.
- Gegenfall: Fehlanwendung (Abstürze oder falsche Ausgaben durch Umwandlung) unter L
  höchstens **1 von 10** häufiger als unter O.

Wird eine Schadensgrenze verletzt, gilt der Pilot als nicht bestanden, auch wenn das
Erfolgskriterium erfüllt ist.

## Trennschärfe

Simuliert mit exaktem einseitigem Fisher-Test, α = 0,05 (`examples/lernkurve/trennschaerfe.py`):

| Läufe je Bedingung | Basis 50 %, +30 pp | Basis 50 %, +40 pp | Basis 40 %, +30 pp |
|---:|---:|---:|---:|
| 20 | 0,53 | 0,84 | 0,46 |
| 30 | 0,71 | 0,95 | 0,67 |
| 40 | 0,84 | 0,99 | 0,80 |

Deshalb 40 Läufe je Bedingung. Mit 20 Läufen würde ein echter Effekt von 30 pp etwa
jedes zweite Mal übersehen. Beispiele bei 20 gegen 20: 12 gegen 6 ergibt p = 0,055,
14 gegen 6 ergibt p = 0,013.

Aufwand Schritt 0 und 1: 3 × 40 + 3 × 10 = 150 Läufe mit je einem Versuch.

## Grenzen

- Ein Fehlertyp zeigt höchstens, ob Transfer in einem sauberen Fall funktioniert, nicht,
  dass er allgemein funktioniert.
- Die Aufgaben stammen von uns; ein Bestehen belegt keine Wirkung auf fremde Projekte.
- Fällt Schritt 1 durch, ist das ein Ergebnis: Dann hilft schon eine korrekte Erfahrung
  im Prompt nicht, und die Frage nach selbst erworbenen Erfahrungen stellt sich so nicht.

## Offene Punkte zur Abstimmung

- Wortlaut der Erfahrung und des Placebos.
- Wer baut Aufgaben und Host (Vorschlag: Codex prüft, Claude baut, oder umgekehrt).
- Ob Schritt 2 und 3 ein eigener Plan werden, nachdem Schritt 1 ausgewertet ist.
