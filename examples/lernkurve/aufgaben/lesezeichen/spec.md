Lesezeichen. Klasse `BookmarkStore(path)`:
- `add(url, title) -> int` legt ein Lesezeichen mit 0 Besuchen an.
- `list() -> list[dict]` mit Einträgen `{"id": int, "url": str, "title": str, "visits": int}`.
- `visit(id)` erhöht die Besuche um 1.
- `remove(id)` löscht ein Lesezeichen.
Die URL muss mit `http://` oder `https://` beginnen und danach Text enthalten.
Leerer Titel oder ungültige URL lösen ValueError aus.

CLI: `add URL TITEL`, `list`, `visit ID`, `remove ID`.
`list` gibt je Lesezeichen eine Zeile `ID TITEL (URL) BESUCHE` aus.
