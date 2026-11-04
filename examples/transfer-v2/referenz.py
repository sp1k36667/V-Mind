"""Referenzlösungen von Transfer v2, aus der Aufgabentabelle erzeugt. Nur für Selbsttest und
Attrappe; dem Modell nie gezeigt.

`quelltext(name, variante)` liefert den vollständigen Inhalt von app.py. Varianten:
- None: korrekt
- "falle": genau die Falle der Gruppe (A: Schlüssel nicht umgewandelt; B: isinstance lässt
  True durch; GA: Postleitzahlen in int umgewandelt; GB: Wahrheitswerte abgelehnt)
- "list_umbenannt": list() heißt list_items (Mechanismus nicht beobachtbar)
- "syntaxfehler": app.py lässt sich nicht laden
- MUTATIONEN: verletzen je eine übrige Anforderung
"""

from aufgaben import AUFGABEN

GEMEINSAM = '''import json
import os
from pathlib import Path


def _text(wert):
    if not isinstance(wert, str) or not wert.strip():
        raise ValueError("Text darf nicht leer sein")
    return wert.strip()


def _zahl(wert):
    if type(wert) is not int or wert <= 0:
        raise ValueError("ganze Zahl größer 0 erwartet")
    return wert


def _laden(pfad, standard, typ):
    if not pfad.exists():
        return standard
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except ValueError as fehler:
        raise ValueError("beschädigte Datei") from fehler
    if not isinstance(daten, dict) or not isinstance(daten.get("items"), typ):
        raise ValueError("beschädigte Datei")
    return daten


def _schreiben(pfad, daten):
    tmp = pfad.with_name(pfad.name + ".tmp")
    tmp.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, pfad)
'''

GRUPPE_A = '''

class {klasse}:
    def __init__(self, path):
        self.path = Path(path)
        daten = _laden(self.path, {{"next_id": 1, "items": {{}}}}, dict)
        self.next_id = int(daten.get("next_id", 1))
        self.items = {{int(k): dict(v) for k, v in daten["items"].items()}}

    def _save(self):
        _schreiben(self.path, {{"next_id": self.next_id, "items": self.items}})

    def _find(self, id):
        if id not in self.items:
            raise ValueError(f"Unbekannte ID: {{id}}")
        return self.items[id]

    def add(self, {f1}, {f2}):
        neu = self.next_id
        self.items[neu] = {{"{f1}": _text({f1}), "{f2}": _text({f2})}}
        self.next_id += 1
        self._save()
        return neu

    def list(self):
        return [{{"id": i, **self.items[i]}} for i in sorted(self.items)]

    def set_{f2}(self, id, {f2}):
        self._find(id)["{f2}"] = _text({f2})
        self._save()

    def remove(self, id):
        self._find(id)
        del self.items[id]
        self._save()
'''

GRUPPE_B = '''

class {klasse}:
    def __init__(self, path):
        self.path = Path(path)
        self.items = [dict(e) for e in _laden(self.path, {{"items": []}}, list)["items"]]

    def _save(self):
        _schreiben(self.path, {{"items": self.items}})

    def add(self, {f1}, {f2}):
        self.items.append({{"{f1}": _text({f1}), "{f2}": _zahl({f2})}})
        self._save()

    def list(self):
        return [dict(e) for e in self.items]

    def total(self):
        return sum(e["{f2}"] for e in self.items)

    def remove(self, index):
        if type(index) is not int or not 0 <= index < len(self.items):
            raise ValueError(f"Unbekannter Index: {{index}}")
        del self.items[index]
        self._save()
'''

GEGENFALL_A = '''

class {klasse}:
    def __init__(self, path):
        self.path = Path(path)
        self.items = {{str(k): str(v) for k, v in _laden(self.path, {{"items": {{}}}}, dict)["items"].items()}}

    def _save(self):
        _schreiben(self.path, {{"items": self.items}})

    def add(self, code, city):
        self.items[_text(code)] = _text(city)
        self._save()

    def city(self, code):
        if code not in self.items:
            raise ValueError(f"Unbekannte Postleitzahl: {{code}}")
        return self.items[code]

    def list(self):
        return [{{"code": c, "city": self.items[c]}} for c in sorted(self.items)]

    def remove(self, code):
        self.city(code)
        del self.items[code]
        self._save()
'''

GEGENFALL_B = '''

def _wahrheitswert(wert):
    if not isinstance(wert, bool):
        raise ValueError("True oder False erwartet")
    return wert


class {klasse}:
    def __init__(self, path):
        self.path = Path(path)
        self.items = [dict(e) for e in _laden(self.path, {{"items": []}}, list)["items"]]

    def _save(self):
        _schreiben(self.path, {{"items": self.items}})

    def _pruefen(self, index):
        if type(index) is not int or not 0 <= index < len(self.items):
            raise ValueError(f"Unbekannter Index: {{index}}")

    def add(self, name, active):
        self.items.append({{"name": _text(name), "active": _wahrheitswert(active)}})
        self._save()

    def list(self):
        return [dict(e) for e in self.items]

    def set_active(self, index, active):
        self._pruefen(index)
        self.items[index]["active"] = _wahrheitswert(active)
        self._save()

    def remove(self, index):
        self._pruefen(index)
        del self.items[index]
        self._save()
'''

VORLAGEN = {"A": GRUPPE_A, "B": GRUPPE_B, "GA": GEGENFALL_A, "GB": GEGENFALL_B}

FALLEN = {
    "A": ("{int(k): dict(v) for k, v in daten", "{k: dict(v) for k, v in daten"),
    "B": ("if type(wert) is not int or wert <= 0:", "if not isinstance(wert, int) or wert <= 0:"),
    "GA": ("{str(k): str(v) for k, v in", "{str(int(k)): str(v) for k, v in"),
    "GB": ("if not isinstance(wert, bool):", "if isinstance(wert, bool) or not isinstance(wert, bool):"),
}

# Mutation -> (Gruppen, alt, neu, Prüfung, die dann scheitern muss)
MUTATIONEN = {
    "leer_erlaubt": ("A B GA GB", "if not isinstance(wert, str) or not wert.strip():",
                     "if not isinstance(wert, str):", None),
    "kaputte_datei_ueberschrieben": ("A B GA GB", 'raise ValueError("beschädigte Datei") from fehler',
                                     "return standard", "test_kaputte_datei_bleibt_erhalten"),
    # GB: Speichern prüft dort nur die Zielprüfung, weil jedes add einen Wahrheitswert braucht.
    "nicht_gespeichert": ("A B GA", "os.replace(tmp, pfad)", "os.remove(tmp)", None),
}


def quelltext(name, variante=None):
    g, klasse, f1, f2, _ = AUFGABEN[name]
    code = GEMEINSAM + VORLAGEN[g].format(klasse=klasse, f1=f1, f2=f2)
    if variante is None:
        return code
    if variante == "falle":
        return _ersetzen(code, *FALLEN[g])
    if variante == "list_umbenannt":
        return _ersetzen(code, "    def list(self):", "    def list_items(self):")
    if variante == "syntaxfehler":
        return code + "\ndef kaputt(:\n"
    _, alt, neu, _ = MUTATIONEN[variante]
    return _ersetzen(code, alt, neu)


def _ersetzen(code, alt, neu):
    if code.count(alt) != 1:
        raise ValueError(f"Ersetzung passt nicht genau einmal: {alt}")
    return code.replace(alt, neu)
