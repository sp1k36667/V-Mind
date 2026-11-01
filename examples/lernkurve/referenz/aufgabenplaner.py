import sys

from basis import JsonStore, cli, text


class TaskStore(JsonStore):
    def add(self, wert):
        return self._new(text=text(wert, "Text"), done=False)

    def done(self, id):
        self._find(id)["done"] = True
        self._save()


def zeilen(store):
    return "\n".join(
        f"{e['id']} [{'x' if e['done'] else ' '}] {e['text']}" for e in store.list()
    )


BEFEHLE = {
    "add": lambda s, t: s.add(t) and None,
    "list": zeilen,
    "done": lambda s, i: s.done(int(i)),
    "remove": lambda s, i: s.remove(int(i)),
}

if __name__ == "__main__":
    sys.exit(cli(TaskStore, BEFEHLE))
