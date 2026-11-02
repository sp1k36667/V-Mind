import sys
from pathlib import Path

from basis import cli, laden, schreiben, text, zahl


class Pantry:
    """Speicherformat {"items": {"<Name>": Menge}}; die Schlüssel sind Namen."""

    def __init__(self, path):
        self.path = Path(path)
        daten = laden(self.path, {"items": {}})
        try:
            self.items = {str(k): zahl(v, "Menge") for k, v in daten["items"].items()}
        except (KeyError, TypeError, ValueError) as fehler:
            raise ValueError(f"Beschädigte Datei: {self.path}") from fehler

    def _save(self):
        schreiben(self.path, {"items": self.items})

    def add(self, name, qty):
        name = text(name, "Name")
        self.items[name] = self.items.get(name, 0) + zahl(qty, "Menge")
        self._save()

    def take(self, name, qty):
        name = text(name, "Name")
        qty = zahl(qty, "Menge")
        if name not in self.items or self.items[name] < qty:
            raise ValueError(f"Nicht genug vorhanden: {name}")
        self.items[name] -= qty
        if self.items[name] == 0:
            del self.items[name]
        self._save()

    def list(self):
        return [{"name": n, "qty": self.items[n]} for n in sorted(self.items)]


BEFEHLE = {
    "add": lambda s, n, m: s.add(n, int(m)),
    "take": lambda s, n, m: s.take(n, int(m)),
    "list": lambda s: "\n".join(f"{e['qty']} x {e['name']}" for e in s.list()),
}

if __name__ == "__main__":
    sys.exit(cli(Pantry, BEFEHLE))
