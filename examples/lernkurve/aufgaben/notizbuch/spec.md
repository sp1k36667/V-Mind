Notizbuch mit Schlagwörtern. Klasse `NoteStore(path)`:
- `add(text, tags) -> int` legt eine Notiz mit einer Liste von Schlagwörtern an.
- `list() -> list[dict]` mit Einträgen `{"id": int, "text": str, "tags": list[str]}`.
- `retag(id, tags)` ersetzt die Schlagwörter einer Notiz.
- `search(tag) -> list[dict]` liefert alle Notizen mit diesem Schlagwort.
- `remove(id)` löscht eine Notiz.
Schlagwörter werden ohne umgebende Leerzeichen und kleingeschrieben gespeichert;
die Suche ignoriert Groß-/Kleinschreibung. Leerer Text und leere Schlagwörter lösen
ValueError aus. Eine leere Schlagwortliste ist erlaubt.

CLI: `add TEXT [TAG ...]`, `list`, `search TAG`, `remove ID`.
`list` und `search` geben je Notiz eine Zeile `ID TEXT [tag1, tag2]` aus.
