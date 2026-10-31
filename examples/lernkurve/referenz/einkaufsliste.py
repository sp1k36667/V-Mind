import sys

from basis import JsonStore, cli, text


def menge(wert):
    if isinstance(wert, bool) or not isinstance(wert, int) or wert <= 0:
        raise ValueError("Menge muss eine ganze Zahl größer 0 sein")
    return wert


class ShoppingList(JsonStore):
    def add(self, name, qty):
        name = text(name, "Name")
        qty = menge(qty)
        for eintrag in self.items:
            if eintrag["name"].lower() == name.lower():
                eintrag["qty"] += qty
                self._save()
                return eintrag["id"]
        return self._new(name=name, qty=qty)

    def set_qty(self, id, qty):
        eintrag = self._find(id)
        eintrag["qty"] = menge(qty)
        self._save()


BEFEHLE = {
    "add": lambda s, n, q: s.add(n, int(q)) and None,
    "list": lambda s: "\n".join(f"{e['id']} {e['qty']} x {e['name']}" for e in s.list()),
    "set": lambda s, i, q: s.set_qty(int(i), int(q)),
    "remove": lambda s, i: s.remove(int(i)),
}

if __name__ == "__main__":
    sys.exit(cli(ShoppingList, BEFEHLE))
