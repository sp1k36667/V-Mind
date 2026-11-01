Einkaufsliste. Klasse `ShoppingList(path)`:
- `add(name, qty) -> int` legt einen Artikel mit Menge an. Gibt es den Namen schon
  (ohne Beachtung von Groß-/Kleinschreibung und umgebenden Leerzeichen), wird die
  Menge zum vorhandenen Artikel addiert und dessen ID zurückgegeben.
- `list() -> list[dict]` mit Einträgen `{"id": int, "name": str, "qty": int}`.
- `set_qty(id, qty)` setzt die Menge.
- `remove(id)` löscht einen Artikel.
Mengen sind ganze Zahlen größer 0, sonst ValueError. Leerer Name löst ValueError aus.

CLI: `add NAME MENGE`, `list`, `set ID MENGE`, `remove ID`.
`list` gibt je Artikel eine Zeile `ID MENGE x NAME` aus.
