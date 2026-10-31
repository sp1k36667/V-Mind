Aufgabenplaner. Klasse `TaskStore(path)`:
- `add(text) -> int` legt eine offene Aufgabe an und liefert ihre ID.
- `list() -> list[dict]` mit Einträgen `{"id": int, "text": str, "done": bool}`.
- `done(id)` markiert eine Aufgabe als erledigt.
- `remove(id)` löscht eine Aufgabe.
Leerer Text löst ValueError aus.

CLI: `add TEXT`, `list`, `done ID`, `remove ID`.
`list` gibt je Aufgabe eine Zeile `ID [ ] TEXT` (offen) oder `ID [x] TEXT` (erledigt) aus.
