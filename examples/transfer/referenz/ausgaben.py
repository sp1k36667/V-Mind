import sys

from basis import IdStore, cli, text, zahl


class ExpenseLog(IdStore):
    def add(self, text_, cents):
        return self._new(text=text(text_, "Text"), cents=zahl(cents, "Betrag"))

    def set_cents(self, id, cents):
        self._find(id)["cents"] = zahl(cents, "Betrag")
        self._save()

    def total(self):
        return sum(e["cents"] for e in self.items.values())


BEFEHLE = {
    "add": lambda s, t, c: str(s.add(t, int(c))),
    "list": lambda s: "\n".join(f"{e['id']} {e['cents']} ct {e['text']}" for e in s.list()),
    "set": lambda s, i, c: s.set_cents(int(i), int(c)),
    "remove": lambda s, i: s.remove(int(i)),
    "total": lambda s: str(s.total()),
}

if __name__ == "__main__":
    sys.exit(cli(ExpenseLog, BEFEHLE))
