import sys

from basis import JsonStore, cli, text


def gueltige_url(wert):
    wert = text(wert, "URL")
    for schema in ("http://", "https://"):
        if wert.startswith(schema) and len(wert) > len(schema):
            return wert
    raise ValueError(f"Ungültige URL: {wert}")


class BookmarkStore(JsonStore):
    def add(self, url, title):
        return self._new(url=gueltige_url(url), title=text(title, "Titel"), visits=0)

    def visit(self, id):
        self._find(id)["visits"] += 1
        self._save()


BEFEHLE = {
    "add": lambda s, u, t: s.add(u, t) and None,
    "list": lambda s: "\n".join(
        f"{e['id']} {e['title']} ({e['url']}) {e['visits']}" for e in s.list()
    ),
    "visit": lambda s, i: s.visit(int(i)),
    "remove": lambda s, i: s.remove(int(i)),
}

if __name__ == "__main__":
    sys.exit(cli(BookmarkStore, BEFEHLE))
