Ausgabenbuch. Klasse `ExpenseLog(path)`:
- `add(text, cents) -> int` erfasst eine Ausgabe in Cent und gibt ihre ID zurück.
- `list() -> list[dict]` mit Einträgen `{"id": int, "text": str, "cents": int}`, nach ID sortiert.
- `set_cents(id, cents)` ändert den Betrag.
- `remove(id)` löscht eine Ausgabe.
- `total() -> int` liefert die Summe aller Beträge in Cent.
Beträge sind ganze Zahlen größer 0, sonst ValueError. Leerer Text löst ValueError aus.

CLI: `add TEXT CENT`, `list`, `set ID CENT`, `remove ID`, `total`.
`list` gibt je Ausgabe eine Zeile `ID CENT ct TEXT` aus.
