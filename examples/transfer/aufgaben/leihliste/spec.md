Leihliste. Klasse `LoanList(path)`:
- `lend(item, person) -> int` vermerkt, dass ein Gegenstand an eine Person verliehen wurde, und gibt die ID zurück.
- `list() -> list[dict]` mit Einträgen `{"id": int, "item": str, "person": str, "returned": bool}`, nach ID sortiert.
- `give_back(id)` vermerkt die Rückgabe; ist der Gegenstand schon zurückgegeben, ValueError.
- `remove(id)` löscht einen Eintrag.
Leerer Gegenstand oder leere Person löst ValueError aus.

CLI: `lend GEGENSTAND PERSON`, `list`, `back ID`, `remove ID`.
`list` gibt je Eintrag eine Zeile `ID GEGENSTAND an PERSON` aus, bei Rückgabe mit dem Zusatz ` (zurück)`.
