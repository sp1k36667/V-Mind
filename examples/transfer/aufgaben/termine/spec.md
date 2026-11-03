Terminkalender. Klasse `Calendar(path)`:
- `add(title, date) -> int` legt einen Termin an; `date` ist ein Text `JJJJ-MM-TT`. Gibt die ID zurück.
- `list() -> list[dict]` mit Einträgen `{"id": int, "title": str, "date": str}`, sortiert nach Datum, bei gleichem Datum nach ID.
- `move(id, date)` verschiebt einen Termin.
- `remove(id)` löscht einen Termin.
Ein Datum, das kein gültiges Kalenderdatum im Format `JJJJ-MM-TT` ist, löst ValueError aus. Leerer Titel löst ValueError aus.

CLI: `add TITEL DATUM`, `list`, `move ID DATUM`, `remove ID`.
`list` gibt je Termin eine Zeile `ID DATUM TITEL` aus.
