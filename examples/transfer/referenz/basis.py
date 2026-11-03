"""Gemeinsame Basis der Referenzlösungen des Transfer-Pilots. Nur für den Selbsttest,
wird dem Modell nie gezeigt."""

import json
import os
import sys
from pathlib import Path


def text(wert, name):
    if not isinstance(wert, str) or not wert.strip():
        raise ValueError(f"{name} darf nicht leer sein")
    return wert.strip()


def zahl(wert, name):
    if isinstance(wert, bool) or not isinstance(wert, int) or wert <= 0:
        raise ValueError(f"{name} muss eine ganze Zahl größer 0 sein")
    return wert


def laden(pfad, standard):
    if not pfad.exists():
        return standard
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except ValueError as fehler:
        raise ValueError(f"Beschädigte Datei: {pfad}") from fehler
    if not isinstance(daten, dict) or not isinstance(daten.get("items"), dict):
        raise ValueError(f"Beschädigte Datei: {pfad}")
    return daten


def schreiben(pfad, daten):
    tmp = pfad.with_name(pfad.name + ".tmp")
    tmp.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, pfad)


class IdStore:
    """Speicherformat {"next_id": int, "items": {"<id>": {...}}}."""

    def __init__(self, path):
        self.path = Path(path)
        daten = laden(self.path, {"next_id": 1, "items": {}})
        try:
            self.next_id = int(daten["next_id"])
            self.items = {int(k): dict(v) for k, v in daten["items"].items()}
        except (KeyError, TypeError, ValueError) as fehler:
            raise ValueError(f"Beschädigte Datei: {self.path}") from fehler

    def _save(self):
        schreiben(self.path, {"next_id": self.next_id, "items": self.items})

    def _new(self, **felder):
        neu = self.next_id
        self.next_id += 1
        self.items[neu] = felder
        self._save()
        return neu

    def _find(self, id):
        if id not in self.items:
            raise ValueError(f"Unbekannte ID: {id}")
        return self.items[id]

    def list(self):
        return [{"id": i, **self.items[i]} for i in sorted(self.items)]

    def remove(self, id):
        self._find(id)
        del self.items[id]
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
