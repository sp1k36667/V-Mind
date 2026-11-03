Rezeptbuch. Klasse `RecipeBook(path)`:
- `add(title, minutes) -> int` legt ein Rezept an und gibt seine ID zurück.
- `list() -> list[dict]` mit Einträgen `{"id": int, "title": str, "minutes": int}`, nach ID sortiert.
- `set_minutes(id, minutes)` ändert die Zubereitungszeit.
- `remove(id)` löscht ein Rezept.
Minuten sind ganze Zahlen größer 0, sonst ValueError. Leerer Titel löst ValueError aus.

CLI: `add TITEL MINUTEN`, `list`, `set ID MINUTEN`, `remove ID`.
`list` gibt je Rezept eine Zeile `ID MINUTEN min TITEL` aus.
