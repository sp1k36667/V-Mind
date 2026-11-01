Kontaktbuch. Klasse `ContactBook(path)`:
- `add(name, email) -> int` legt einen Kontakt an.
- `list() -> list[dict]` mit Einträgen `{"id": int, "name": str, "email": str}`.
- `update_email(id, email)` ändert die E-Mail-Adresse.
- `remove(id)` löscht einen Kontakt.
Eine gültige E-Mail enthält genau ein `@`, davor und danach Text, und nach dem `@`
einen Punkt mit Text davor und danach. E-Mails sind eindeutig, ohne Beachtung von
Groß-/Kleinschreibung. Leerer Name, ungültige oder doppelte E-Mail lösen ValueError aus.

CLI: `add NAME EMAIL`, `list`, `email ID EMAIL`, `remove ID`.
`list` gibt je Kontakt eine Zeile `ID NAME <EMAIL>` aus.
