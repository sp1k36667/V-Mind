import datetime
import sys

from basis import IdStore, cli, text


def datum(wert):
    try:
        if not isinstance(wert, str) or len(wert) != 10:
            raise ValueError
        datetime.date.fromisoformat(wert)
    except ValueError as fehler:
        raise ValueError(f"Ungültiges Datum: {wert}") from fehler
    return wert


class Calendar(IdStore):
    def add(self, title, date):
        return self._new(title=text(title, "Titel"), date=datum(date))

    def list(self):
        return sorted(super().list(), key=lambda e: (e["date"], e["id"]))

    def move(self, id, date):
        self._find(id)["date"] = datum(date)
        self._save()


BEFEHLE = {
    "add": lambda s, t, d: str(s.add(t, d)),
    "list": lambda s: "\n".join(f"{e['id']} {e['date']} {e['title']}" for e in s.list()),
    "move": lambda s, i, d: s.move(int(i), d),
    "remove": lambda s, i: s.remove(int(i)),
}

if __name__ == "__main__":
    sys.exit(cli(Calendar, BEFEHLE))
