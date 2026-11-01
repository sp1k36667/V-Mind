import sys

from basis import JsonStore, cli, text

TAGESMINUTEN = 1440


def minuten(wert):
    if isinstance(wert, bool) or not isinstance(wert, int) or not 0 <= wert <= TAGESMINUTEN:
        raise ValueError(f"Ungültige Zeit: {wert}")
    return wert


class TimeLog(JsonStore):
    def add(self, project, start, end):
        project = text(project, "Projekt")
        start, end = minuten(start), minuten(end)
        if end <= start:
            raise ValueError("Ende muss nach dem Start liegen")
        for eintrag in self.items:
            if start < eintrag["end"] and eintrag["start"] < end:
                raise ValueError("Zeitspanne überschneidet sich")
        return self._new(project=project, start=start, end=end)

    def rename(self, id, project):
        eintrag = self._find(id)
        eintrag["project"] = text(project, "Projekt")
        self._save()

    def total(self, project):
        return sum(e["end"] - e["start"] for e in self.items if e["project"] == project)


BEFEHLE = {
    "add": lambda s, p, a, e: s.add(p, int(a), int(e)) and None,
    "list": lambda s: "\n".join(
        f"{e['id']} {e['project']} {e['start']}-{e['end']}" for e in s.list()
    ),
    "total": lambda s, p: str(s.total(p)),
    "remove": lambda s, i: s.remove(int(i)),
}

if __name__ == "__main__":
    sys.exit(cli(TimeLog, BEFEHLE))
