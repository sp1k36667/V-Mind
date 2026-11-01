import sys

from basis import JsonStore, cli, text


def schlagwoerter(tags):
    return [text(t, "Schlagwort").lower() for t in tags]


class NoteStore(JsonStore):
    def add(self, wert, tags):
        return self._new(text=text(wert, "Text"), tags=schlagwoerter(tags))

    def retag(self, id, tags):
        eintrag = self._find(id)
        eintrag["tags"] = schlagwoerter(tags)
        self._save()

    def search(self, tag):
        gesucht = text(tag, "Schlagwort").lower()
        return [e for e in self.list() if gesucht in e["tags"]]


def zeilen(eintraege):
    return "\n".join(f"{e['id']} {e['text']} [{', '.join(e['tags'])}]" for e in eintraege)


BEFEHLE = {
    "add": lambda s, t, *tags: s.add(t, list(tags)) and None,
    "list": lambda s: zeilen(s.list()),
    "search": lambda s, t: zeilen(s.search(t)),
    "remove": lambda s, i: s.remove(int(i)),
}

if __name__ == "__main__":
    sys.exit(cli(NoteStore, BEFEHLE))
