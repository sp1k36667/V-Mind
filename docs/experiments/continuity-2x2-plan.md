# Fortsetzungs-Folgelauf 2x2 – vorab festgelegter Plan

Status: zum Einfrieren vorgelegt, Codex' Prüfpunkte (Teamkanal #73) eingearbeitet.
Maßgeblich ist der Commit, der diesen Plan zusammen mit `examples/continuity/run_2x2.py`
enthält; sein Hash steht im Bericht. Kein Lauf vor Codex' unabhängigem Selbsttest. Hintergrund: [erster Fortsetzungspilot](continuity-pilot.md)
(negativ: V 117/165, M 133/165).

## Frage

Der erste Pilot fand zwei mögliche Ursachen für den Rückstand der JSON-Übergabe:
überholte Zustandsereignisse im `resume`-Fenster (V nannte neunmal einen alten nächsten
Schritt) und die Darstellung (verschachteltes JSON gegen flache Feldliste). Seit
f538c49 lässt `resume` überholte Ziel-, Aufgaben- und nächste-Schritt-Meldungen aus
`recent_events` weg. Dieser Lauf trennt beide Faktoren:

1. **Filter:** Nennt das Modell seltener einen überholten Wert, wenn `resume` keine
   überholten Zustände mehr zeigt?
2. **Format:** Wie groß ist bei gleicher Information der Unterschied zwischen JSON und
   flacher Feldliste, wenn das Antwortformat vom Host per JSON-Schema abgesichert ist?

## Bedingungen (2x2)

| | vor dem Filter (Binary aus 102b1a5) | mit Filter (Binary aus a49959a) |
|---|---|---|
| JSON-`resume` | J0 | Ja |
| flache Feldliste desselben Snapshots | T0 | Ta |

Jede Projektdatenbank wird mit dem aktuellen Binary gebaut; nur der `resume`-Aufruf
unterscheidet sich. T0 und Ta enthalten exakt dieselben Werte wie J0 und Ja, nur anders
dargestellt (gleiche Funktion wie im ersten Pilot). Das Modell nutzt keine Werkzeuge.

Die Ergebnisse werden **nicht** mit dem ersten Pilot verrechnet: Projekte, Seeds und die
Ausgabebedingung (Schema statt freiem JSON) sind neu.

## Material

Vier neue synthetische Projekte (`kran`, `fluss`, `mosaik`, `leuchte`) mit 5 bis 8
Aufgaben und 5 bis 12 Notizen. Werte stehen nicht am Satzende, damit Satzzeichen nicht
am Wert hängen. Jedes Projekt hat bekannte überholte Werte: altes Ziel (Release-Kennung),
D1 „Backend PostgreSQL“ (durch D2 ersetzt), Aufgabenstatus `schema: in_progress` und
`search: blocked`, zwei frühere nächste Schritte.

In den Projekten 0 bis 2 liegen die Notizen vor den letzten Zustandsänderungen; dort
stehen unter J0/T0 die beiden alten nächsten Schritte im `recent_events`-Fenster, unter
Ja/Ta nicht (vom Selbsttest geprüft). Projekt 3 ist die **Kontrolle**: Die Notizen liegen
nach allen Zustandsänderungen, das Fenster ist vor und nach dem Filter gleich. Altes Ziel
und alte Aufgabenstatus liegen in allen Projekten und Stufen außerhalb des Fensters; D1
ist als Entscheidung in allen Stufen sichtbar.

Elf Fragen wie im ersten Pilot: acht verfügbare Fakten, die Archiv-Portnummer (nur in der
älteren Historie, in keinem Snapshot) und zwei unbeantwortbare Angaben.

## Durchführung

4 Projekte × 4 Bedingungen × 5 Seeds (4101 bis 4105) = 80 Aufrufe, je Projekt und Seed in
zufälliger Reihenfolge (Startwert 314159). Gemma 4 12B Q4_0 wie im ersten Pilot,
Temperatur 0,7, `num_ctx` 8192, `num_predict` 512, `keep_alive` 0. Ollama `format` ist
für alle Bedingungen dasselbe JSON-Schema: alle elf Schlüssel Pflicht, nur Strings,
keine weiteren Felder, keine vorgegebenen Werte. Ein Versuch je Zelle, keine
Wiederholung, kein Ersetzen. Leeres neues Ausgabeverzeichnis. Gespeichert werden
Rohantworten (ohne Ollama-Feld `context`, das nur Token-IDs enthält), Metadaten mit
Modell-Digest und SHA-256 von Harness und beiden Binaries.

## Bewertung

- **Streng (primär):** exakter Wert nach Entfernen äußeren Leerraums.
- **Mild (sekundär, getrennt berichtet), genau in dieser Reihenfolge:** Leerraum außen
  entfernen, äußere Anführungszeichen `" ' „ “ ”` entfernen, Leerraum entfernen,
  abschließende `. , ; :` entfernen, Leerraum entfernen; danach zählt `unbekannt` in
  beliebiger Groß-/Kleinschreibung als `unbekannt`. Keine weitere Angleichung, auch nicht
  nachträglich.
- **Überholter Wert:** Die Antwort enthält einen der bekannten alten Werte der Frage und
  nicht den aktuellen Wert (Fragen `release`, `backend`, `schema`, `search`, `next`).
- **Erfindung:** bei `password` oder `production_date` ein Wert, der mild nicht
  `unbekannt` ist.
- Parse- und Formatfehler werden gezählt; fehlende Antworten sind falsch.

## Vorab festgelegte Kriterien (beschreibend, keine Signifikanzaussage)

Die Kriterien sind in `acceptance()` des Harness umgesetzt; `summary.json` enthält ihr
Ergebnis. Der Selbsttest prüft vor jedem Lauf mit künstlichen Antworten, dass leere
Antworten sicher scheitern und dass „unentschieden“, „nicht besser“ und „besser“ richtig
erkannt werden.

1. **Untergrenzen für Ja und Ta, jede einzeln:** 20 ausgewertete Aufrufe, keine
   technischen Fehler, keine Formatfehler, mindestens 144 von 160 Fakten mild richtig,
   mindestens 39 von 40 unbeantwortbaren Angaben mild als `unbekannt`, keine Erfindung.
   Fehlende Antworten zählen als falsch, nie als korrektes Unwissen.
2. **Filterwirkung**, gemessen an `next` in den Projekten 0 bis 2 (je Bedingung 15
   Aufrufe), getrennt für J (J0 gegen Ja) und T (T0 gegen Ta):
   - „nicht besser“, wenn der neue Arm mehr als einmal einen überholten Schritt nennt
     oder nicht seltener als ein alter Arm mit Fehlern;
   - „unentschieden“, wenn der alte Arm keinen überholten Schritt nennt und der neue
     ebenfalls keinen: Dann gibt es nichts zu beheben, eine Filterwirkung ist nicht messbar;
   - „besser“, wenn der alte Arm mindestens einen überholten Schritt nennt und der neue
     höchstens einen und weniger als der alte.

   Filter insgesamt: „nicht bestanden“, sobald ein Paar „nicht besser“ ist; „bestanden“,
   wenn mindestens ein Paar „besser“ und keines „nicht besser“ ist; sonst „unentschieden“.
3. **Format:** Ja liegt bei den Fakten (mild) höchstens 8 Antworten unter Ta. Der
   Unterschied wird in beide Richtungen berichtet.
4. **Kontrolle:** In Projekt 3 sind vollständiger Snapshot und Prompt vor und nach dem
   Filter identisch (vom Selbsttest geprüft; Prompt-Hash je Aufruf gespeichert).
   Unterschiede dort zeigen nur die Streuung durch den Zufall und werden beschreibend
   berichtet.

**Bestanden** heißt: 1 für Ja und Ta erfüllt, Filter „bestanden“, 3 erfüllt. Ein
„unentschieden“ beim Filter ist kein Bestehen. Ein Bestehen ist eine lokale,
beschreibende Schwelle dieses synthetischen Aufbaus und kein Nachweis der
Gleichwertigkeit oder Überlegenheit gegenüber anderen Übergaben. Es zeigt keinen Vorteil
gegenüber einer von Menschen geschriebenen Übergabe, keine Lernwirkung und nichts über
reale Projekte. Ein negatives Ergebnis wird mit unveränderten Kriterien veröffentlicht.

## Ergebnisse je Frage

Berichtet werden je Bedingung, Projekt und Frage: streng, mild, überholte Werte,
Erfindungen, Formatfehler, Archivport als unbekannt; dazu Promptgröße und Laufzeit.
