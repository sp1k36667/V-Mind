Zeiterfassung. Klasse `TimeLog(path)`:
- `add(project, start, end) -> int` erfasst eine Zeitspanne. `start` und `end` sind
  Minuten seit Mitternacht (ganze Zahlen von 0 bis 1440), `end` muss größer als `start` sein.
- `list() -> list[dict]` mit Einträgen `{"id": int, "project": str, "start": int, "end": int}`.
- `rename(id, project)` ändert den Projektnamen.
- `total(project) -> int` liefert die Summe der Minuten eines Projekts (0, wenn keines).
- `remove(id)` löscht einen Eintrag.
Zeitspannen dürfen sich nicht überschneiden, egal welches Projekt; direkt aneinander
grenzende Spannen sind erlaubt. Leerer Projektname, ungültige Zeiten oder
Überschneidungen lösen ValueError aus.

CLI: `add PROJEKT START ENDE`, `list`, `total PROJEKT`, `remove ID`.
`list` gibt je Eintrag eine Zeile `ID PROJEKT START-ENDE` aus, `total` die Minutenzahl.
