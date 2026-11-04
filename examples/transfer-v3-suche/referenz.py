"""Referenzlösungen der Aufgabensuche. Nur für Selbsttest und Attrappe; dem Modell nie gezeigt.

`quelltext(name, variante)` liefert den vollständigen Inhalt von app.py. Varianten:
- None: korrekt
- "falle": genau die Falle der Aufgabe, sonst korrekt
- "umbenannt": das Hauptsymbol heißt anders (Mechanismus nicht beobachtbar)
- "syntaxfehler": app.py lässt sich nicht laden
- Schlüssel aus MUTATIONEN[name]: verletzen je eine übrige Anforderung
"""

from aufgaben import symbol

KORREKT = {
    "datumsimport": '''import datetime
import re


def parse_date(text):
    if not isinstance(text, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
        raise ValueError("Format JJJJ-MM-TT erwartet")
    return datetime.datetime.strptime(text, "%Y-%m-%d").date()
''',
    "kalender": '''def _minute(wert):
    if type(wert) is not int or not 0 <= wert <= 1440:
        raise ValueError("Minute von 0 bis 1440 erwartet")
    return wert


class Calendar:
    def __init__(self):
        self._eintraege = []

    def reserve(self, start_min, end_min):
        start, ende = _minute(start_min), _minute(end_min)
        if start >= ende:
            raise ValueError("Beginn muss vor dem Ende liegen")
        if any(start < e and s < ende for s, e in self._eintraege):
            return False
        self._eintraege.append((start, ende))
        return True

    def bookings(self):
        return sorted(self._eintraege)
''',
    "warteliste": '''class Waitlist:
    def __init__(self, capacity):
        if type(capacity) is not int or capacity < 1:
            raise ValueError("Kapazität ab 1 erwartet")
        self._kapazitaet = capacity
        self._buchungen = []

    def book(self, name):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Name darf nicht leer sein")
        nummer = len(self._buchungen) + 1
        self._buchungen.append([nummer, name, True])
        return nummer

    def cancel(self, booking_id):
        for eintrag in self._buchungen:
            if eintrag[0] == booking_id:
                if not eintrag[2]:
                    raise ValueError("Buchung bereits storniert")
                eintrag[2] = False
                return
        raise ValueError("unbekannte Buchung")

    def _aktive(self):
        return [name for _, name, aktiv in self._buchungen if aktiv]

    def confirmed(self):
        return self._aktive()[:self._kapazitaet]

    def waiting(self):
        return self._aktive()[self._kapazitaet:]
''',
    "paketstatus": '''STATUS = ["created", "in_transit", "out_for_delivery", "delivered"]


class Package:
    def __init__(self):
        self._status = "created"

    def apply(self, event):
        if not isinstance(event, str) or event not in STATUS:
            raise ValueError("unbekanntes Ereignis")
        if STATUS.index(event) > STATUS.index(self._status):
            self._status = event

    def status(self):
        return self._status
''',
    "bestellimport": '''import json
import os
from pathlib import Path


class Importer:
    def __init__(self, path):
        self._pfad = Path(path)
        self._summe, self._gesehen = 0, set()
        if self._pfad.exists():
            daten = json.loads(self._pfad.read_text(encoding="utf-8"))
            self._summe, self._gesehen = int(daten["total"]), set(daten["seen"])

    def _speichern(self):
        tmp = self._pfad.with_name(self._pfad.name + ".tmp")
        tmp.write_text(json.dumps({"total": self._summe, "seen": sorted(self._gesehen)}),
                       encoding="utf-8")
        os.replace(tmp, self._pfad)

    def ingest(self, event_id, cents):
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event_id darf nicht leer sein")
        if type(cents) is not int or cents <= 0:
            raise ValueError("cents muss eine ganze Zahl größer 0 sein")
        if event_id in self._gesehen:
            return False
        self._gesehen.add(event_id)
        self._summe += cents
        self._speichern()
        return True

    def total(self):
        return self._summe
''',
    "lager": '''def _menge(wert, minimum):
    if type(wert) is not int or wert < minimum:
        raise ValueError("ungültige Menge")
    return wert


class Stock:
    def __init__(self, initial):
        self._bestand = _menge(initial, 0)

    def deposit(self, quantity):
        self._bestand += _menge(quantity, 1)

    def withdraw(self, quantity):
        menge = _menge(quantity, 1)
        if menge > self._bestand:
            raise ValueError("Bestand reicht nicht")
        self._bestand -= menge

    def balance(self):
        return self._bestand
''',
}

# Name -> (alt, neu): genau die Falle, als Ersetzung im korrekten Quelltext.
FALLEN = {
    "datumsimport": ('''    if not isinstance(text, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
''', '''    if not isinstance(text, str):
'''),
    "kalender": ("start < e and s < ende", "start <= e and s <= ende"),
    "warteliste": ('''                if not eintrag[2]:
                    raise ValueError("Buchung bereits storniert")
''', ""),
    "paketstatus": ('''        if STATUS.index(event) > STATUS.index(self._status):
            self._status = event
''', '''        self._status = event
'''),
    "bestellimport": ('''            self._summe, self._gesehen = int(daten["total"]), set(daten["seen"])
''', '''            self._summe = int(daten["total"])
'''),
    "lager": ('''        if menge > self._bestand:
            raise ValueError("Bestand reicht nicht")
        self._bestand -= menge
''', '''        self._bestand -= menge
        if self._bestand < 0:
            raise ValueError("Bestand reicht nicht")
'''),
}

# Name -> {Mutation: (alt, neu, erwartete übrige Prüfung)}
MUTATIONEN = {
    "datumsimport": {
        "kalendertag_ungeprueft": ('''    return datetime.datetime.strptime(text, "%Y-%m-%d").date()
''', '''    jahr, monat, tag = (int(t) for t in text.split("-"))
    return datetime.date(jahr, min(max(monat, 1), 12), min(max(tag, 1), 28))
''', "test_ungueltiger_kalendertag_valueerror"),
        "typfehler_statt_valueerror": ('''    if not isinstance(text, str) or not re''', '''    if not re''',
                                       "test_kein_text_valueerror"),
    },
    "kalender": {
        "ueberschneidung_erlaubt": ('''            return False
''', '''            pass
''', "test_ueberschneidungen_abgelehnt"),
        "unsortiert": ("return sorted(self._eintraege)", "return list(self._eintraege)",
                       "test_sortiert"),
        "grenzen_offen": ("not 0 <= wert <= 1440", "False", "test_ungueltige_zeiten_valueerror"),
    },
    "warteliste": {
        "kein_nachruecken": ("return self._aktive()[:self._kapazitaet]",
                             "return [n for _, n, a in self._buchungen[:self._kapazitaet] if a]",
                             "test_nachruecken"),
        "unbekannt_still": ('''        raise ValueError("unbekannte Buchung")
''', '''        return
''', "test_unbekannte_id_valueerror"),
        "leerer_name": ("or not name.strip()", "or False", "test_ungueltige_werte_valueerror"),
    },
    "paketstatus": {
        "unbekannt_angenommen": ('''        if not isinstance(event, str) or event not in STATUS:
            raise ValueError("unbekanntes Ereignis")
        if STATUS.index(event) > STATUS.index(self._status):
''', '''        if event in STATUS and STATUS.index(event) > STATUS.index(self._status):
''', "test_unbekanntes_ereignis_valueerror"),
        "kein_ueberspringen": ("STATUS.index(event) > STATUS.index(self._status)",
                               "STATUS.index(event) == STATUS.index(self._status) + 1",
                               "test_ueberspringen"),
    },
    "bestellimport": {
        "summe_nicht_gespeichert": ('''            self._summe, self._gesehen = int(daten["total"]), set(daten["seen"])
''', '''            self._gesehen = set(daten["seen"])
''', "test_summe_dauerhaft"),
        "duplikat_gezaehlt": ('''        if event_id in self._gesehen:
            return False
''', "", "test_duplikat_in_derselben_instanz"),
        "cents_ungeprueft": ("type(cents) is not int or cents <= 0", "False",
                             "test_ungueltige_werte_valueerror"),
    },
    "lager": {
        "einlagern_falsch": ("self._bestand += _menge(quantity, 1)", "self._bestand = _menge(quantity, 1)",
                             "test_einlagern"),
        "null_verboten": ("if menge > self._bestand:", "if menge >= self._bestand:",
                          "test_bis_null_entnehmen"),
        "anfang_ungeprueft": ("self._bestand = _menge(initial, 0)", "self._bestand = initial",
                              "test_ungueltiger_anfangsbestand_valueerror"),
    },
}


def _ersetzen(quelle, alt, neu):
    if quelle.count(alt) != 1:
        raise ValueError(f"Ersetzung nicht eindeutig: {alt!r}")
    return quelle.replace(alt, neu)


def quelltext(name, variante=None):
    quelle = KORREKT[name]
    if variante is None:
        return quelle
    if variante == "falle":
        return _ersetzen(quelle, *FALLEN[name])
    if variante == "umbenannt":
        return quelle.replace(f"class {symbol(name)}", f"class {symbol(name)}Alt").replace(
            f"def {symbol(name)}(", f"def {symbol(name)}_alt(")
    if variante == "syntaxfehler":
        return quelle + "\ndef kaputt(:\n"
    alt, neu, _ = MUTATIONEN[name][variante]
    return _ersetzen(quelle, alt, neu)
