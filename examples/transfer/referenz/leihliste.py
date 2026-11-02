import sys

from basis import IdStore, cli, text


class LoanList(IdStore):
    def lend(self, item, person):
        return self._new(item=text(item, "Gegenstand"), person=text(person, "Person"),
                         returned=False)

    def give_back(self, id):
        eintrag = self._find(id)
        if eintrag["returned"]:
            raise ValueError(f"Schon zurückgegeben: {id}")
        eintrag["returned"] = True
        self._save()


def zeile(e):
    return f"{e['id']} {e['item']} an {e['person']}" + (" (zurück)" if e["returned"] else "")


BEFEHLE = {
    "lend": lambda s, g, p: str(s.lend(g, p)),
    "list": lambda s: "\n".join(zeile(e) for e in s.list()),
    "back": lambda s, i: s.give_back(int(i)),
    "remove": lambda s, i: s.remove(int(i)),
}

if __name__ == "__main__":
    sys.exit(cli(LoanList, BEFEHLE))
