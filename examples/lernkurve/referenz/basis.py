"""Gemeinsame Basis der Referenzlösungen. Nur für den Selbsttest der Abnahmen,
wird dem Modell nie gezeigt."""

import json
import os
import sys
from pathlib import Path


def text(wert, name):
    if not isinstance(wert, str) or not wert.strip():
        raise ValueError(f"{name} darf nicht leer sein")
    return wert.strip()


class JsonStore:
    def __init__(self, path):
        self.path = Path(path)
        self.next_id = 1
        self.items = []
        if self.path.exists():
            try:
                daten = json.loads(self.path.read_text(encoding="utf-8"))
                self.next_id = int(daten["next_id"])
                self.items = list(daten["items"])
            except (ValueError, KeyError, TypeError) as fehler:
                raise ValueError(f"Beschädigte Datei: {self.path}") from fehler

    def _save(self):
        tmp = self.path.with_name(self.path.name + ".tmp")
        inhalt = {"next_id": self.next_id, "items": self.items}
        tmp.write_text(json.dumps(inhalt, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    def _new(self, **felder):
        neu = self.next_id
        self.next_id += 1
        self.items.append({"id": neu, **felder})
        self._save()
        return neu

    def _find(self, id):
        for eintrag in self.items:
            if eintrag["id"] == id:
                return eintrag
        raise ValueError(f"Unbekannte ID: {id}")

    def list(self):
        return [dict(e) for e in self.items]

    def remove(self, id):
        self.items.remove(self._find(id))
        self._save()


def cli(klasse, befehle, argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        if len(argv) < 3 or argv[0] != "--file":
            raise ValueError("Aufruf: --file DATEI BEFEHL ...")
        store = klasse(argv[1])
        befehl = befehle.get(argv[2])
        if befehl is None:
            raise ValueError(f"Unbekannter Befehl: {argv[2]}")
        ausgabe = befehl(store, *argv[3:])
    except (ValueError, TypeError) as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 1
    if ausgabe is not None:
        print(ausgabe)
    return 0
