import sys

from basis import IdStore, cli, text, zahl


class RecipeBook(IdStore):
    def add(self, title, minutes):
        return self._new(title=text(title, "Titel"), minutes=zahl(minutes, "Minuten"))

    def set_minutes(self, id, minutes):
        self._find(id)["minutes"] = zahl(minutes, "Minuten")
        self._save()


BEFEHLE = {
    "add": lambda s, t, m: str(s.add(t, int(m))),
    "list": lambda s: "\n".join(f"{e['id']} {e['minutes']} min {e['title']}" for e in s.list()),
    "set": lambda s, i, m: s.set_minutes(int(i), int(m)),
    "remove": lambda s, i: s.remove(int(i)),
}

if __name__ == "__main__":
    sys.exit(cli(RecipeBook, BEFEHLE))
