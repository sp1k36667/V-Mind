Vorratsliste. Klasse `Pantry(path)`:
- `add(name, qty)` erhöht den Bestand eines Artikels um `qty`; ein neuer Name legt den Artikel an. Namen werden ohne umgebende Leerzeichen gespeichert, Groß-/Kleinschreibung zählt.
- `take(name, qty)` verringert den Bestand; erreicht er 0, wird der Artikel entfernt. Mehr als vorhanden oder ein unbekannter Name löst ValueError aus.
- `list() -> list[dict]` mit Einträgen `{"name": str, "qty": int}`, nach Name sortiert.
Mengen sind ganze Zahlen größer 0, sonst ValueError. Leerer Name löst ValueError aus.

CLI: `add NAME MENGE`, `take NAME MENGE`, `list`.
`list` gibt je Artikel eine Zeile `MENGE x NAME` aus.
