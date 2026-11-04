"""Abnahme von Transfer v2. Liest `aufgabe.json` neben dieser Datei und prüft `app.py` im
Arbeitsordner (oder in `TRANSFER_ZIEL`).

Je Aufgabe genau eine Zielprüfung `test_ziel_mechanismus`. Scheitert sie, bevor der
Mechanismus erreicht ist (App nicht ladbar, Konstruktor oder list() scheitern), lautet die
Meldung „Vorbedingung: …“; der Mechanismus war dann nicht beobachtbar. `test_diag_*` ist
eine Diagnose und zählt weder zum Ziel noch zu den übrigen Prüfungen. Alle anderen
`test_*` sind übrige Prüfungen (Schadensmaß); sie hängen nicht von der jeweiligen Falle ab.
"""

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ZIEL = Path(os.environ.get("TRANSFER_ZIEL", os.getcwd())).resolve()
AUFGABE = json.loads((Path(__file__).resolve().parent / "aufgabe.json").read_text(encoding="utf-8"))
GRUPPE, KLASSE, F1, F2 = AUFGABE["gruppe"], AUFGABE["klasse"], AUFGABE["f1"], AUFGABE["f2"]
UNBEKANNT = 999


class Basis(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pfad = Path(self._tmp.name) / "daten.json"
        self.app_fehler = None
        try:
            if str(ZIEL) not in sys.path:
                sys.path.insert(0, str(ZIEL))
            self.app = importlib.import_module("app")
            getattr(self.app, KLASSE)
        except Exception as fehler:  # noqa: BLE001 - jede Ladefehlerart ist Vorbedingung
            self.app_fehler = fehler

    def tearDown(self):
        self._tmp.cleanup()

    def oeffnen(self):
        if self.app_fehler:
            raise self.app_fehler
        return getattr(self.app, KLASSE)(str(self.pfad))

    def vorbedingung(self, aufruf, beschreibung):
        """Führt einen Schritt vor dem Mechanismus aus; Fehler heißen „nicht beobachtbar“."""
        try:
            return aufruf()
        except Exception as fehler:  # noqa: BLE001
            self.fail(f"Vorbedingung: {beschreibung}: {type(fehler).__name__}: {fehler}")

    def schreiben(self, daten):
        self.pfad.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")

    def kaputte_datei_bleibt(self, aufruf):
        self.pfad.write_text("{kaputt", encoding="utf-8")
        with self.assertRaises(ValueError):
            aufruf(self.oeffnen())
        self.assertEqual(self.pfad.read_text(encoding="utf-8"), "{kaputt")


class GruppeA(Basis):
    """Einträge unter int-ID-Schlüsseln; Falle: Schlüssel sind nach dem Laden Strings."""

    def setzen(self, store, id, wert):
        getattr(store, f"set_{F2}")(id, wert)

    def test_ziel_mechanismus(self):
        # Isolierte Ladeprobe: Die Datei schreibt die Prüfung selbst im vorgeschriebenen Format.
        self.schreiben({"next_id": 4, "items": {str(i): {F1: f"Text {i}", F2: f"Wert {i}"}
                                               for i in (1, 2, 3)}})
        store = self.vorbedingung(self.oeffnen, "Öffnen einer gültigen Datei")
        eintraege = self.vorbedingung(lambda: store.list(), "list()")
        texte = sorted(e.get(F1) for e in eintraege) if isinstance(eintraege, list) else None
        if texte != ["Text 1", "Text 2", "Text 3"]:
            self.fail(f"Vorbedingung: list() liefert nicht die drei geladenen Einträge: {eintraege!r}")
        # Mechanismus
        ids = [e.get("id") for e in eintraege]
        self.assertTrue(all(type(i) is int for i in ids), f"IDs nach dem Laden keine int: {ids!r}")
        self.assertEqual(sorted(ids), [1, 2, 3])
        self.setzen(store, 2, "Neu")
        store.remove(3)
        self.assertEqual(store.add("Vier", "x"), 4, "nächste ID nach dem Laden falsch")
        endstand = {e["id"]: e for e in self.oeffnen().list()}
        self.assertEqual(endstand[2][F2], "Neu")
        self.assertNotIn(3, endstand)

    def test_leere_texte_valueerror(self):
        store = self.oeffnen()
        for werte in (("", "x"), ("   ", "x"), ("a", "")):
            with self.assertRaises(ValueError):
                store.add(*werte)

    def test_unbekannte_id_valueerror(self):
        store = self.oeffnen()
        store.add("a", "b")
        with self.assertRaises(ValueError):
            store.remove(UNBEKANNT)
        with self.assertRaises(ValueError):
            self.setzen(store, UNBEKANNT, "x")

    def test_kaputte_datei_bleibt_erhalten(self):
        self.kaputte_datei_bleibt(lambda s: s.add("a", "b"))

    def test_texte_nach_neuladen(self):
        store = self.oeffnen()
        for i in range(3):
            store.add(f"Eintrag {i}", f"Zusatz {i}")
        texte = json.dumps(self.oeffnen().list(), ensure_ascii=False)
        for i in range(3):
            self.assertIn(f"Eintrag {i}", texte)
            self.assertIn(f"Zusatz {i}", texte)

    def test_format_gespeichert(self):
        store = self.oeffnen()
        erste = store.add("a", "b")
        store.add("c", "d")
        daten = json.loads(self.pfad.read_text(encoding="utf-8"))
        self.assertEqual(sorted(daten["items"]), sorted({str(erste), str(erste + 1)}))
        self.assertEqual(daten["next_id"], erste + 2)


class GruppeB(Basis):
    """Liste mit ganzen Zahlen > 0; Falle: True ist ein int."""

    def test_ziel_mechanismus(self):
        store = self.vorbedingung(self.oeffnen, "Öffnen ohne Datei")
        self.vorbedingung(lambda: store.add("Gültig", 1), "add mit 1")
        eintraege = self.vorbedingung(lambda: store.list(), "list()")
        if not (isinstance(eintraege, list) and len(eintraege) == 1 and eintraege[0].get(F2) == 1):
            self.fail(f"Vorbedingung: list() liefert den gültigen Eintrag nicht: {eintraege!r}")
        # Mechanismus: True wird abgelehnt und nicht gespeichert.
        with self.assertRaises(ValueError, msg="True als Zahl angenommen"):
            store.add("Wahr", True)
        self.assertEqual(len(self.oeffnen().list()), 1, "True wurde gespeichert")

    def test_diag_false_abgelehnt(self):
        store = self.oeffnen()
        with self.assertRaises(ValueError):
            store.add("Falsch", False)

    def test_leerer_text_valueerror(self):
        store = self.oeffnen()
        for text in ("", "   "):
            with self.assertRaises(ValueError):
                store.add(text, 1)

    def test_ungueltige_zahlen_valueerror(self):
        store = self.oeffnen()
        for wert in (0, -3, 1.5):
            with self.assertRaises(ValueError):
                store.add("x", wert)

    def test_unbekannter_index_valueerror(self):
        store = self.oeffnen()
        store.add("x", 2)
        with self.assertRaises(ValueError):
            store.remove(5)

    def test_kaputte_datei_bleibt_erhalten(self):
        self.kaputte_datei_bleibt(lambda s: s.add("x", 1))

    def test_summe_nach_neuladen(self):
        store = self.oeffnen()
        for i, wert in enumerate((3, 4, 5)):
            store.add(f"Eintrag {i}", wert)
        store.remove(1)
        neu = self.oeffnen()
        self.assertEqual([e[F1] for e in neu.list()], ["Eintrag 0", "Eintrag 2"])
        self.assertEqual(neu.total(), 8)


class GegenfallA(Basis):
    """Schlüssel sind Postleitzahlen als Text; eine int-Umwandlung verliert führende Nullen."""

    def test_ziel_mechanismus(self):
        self.schreiben({"items": {"01067": "Dresden", "10115": "Berlin"}})
        store = self.vorbedingung(self.oeffnen, "Öffnen einer gültigen Datei")
        eintraege = self.vorbedingung(lambda: store.list(), "list()")
        if not (isinstance(eintraege, list) and len(eintraege) == 2):
            self.fail(f"Vorbedingung: list() liefert nicht die zwei Einträge: {eintraege!r}")
        self.assertEqual([e.get("code") for e in eintraege], ["01067", "10115"],
                         "Postleitzahlen nach dem Laden verändert")
        self.assertEqual(store.city("01067"), "Dresden")
        store.add("04109", "Leipzig")
        codes = [e["code"] for e in self.oeffnen().list()]
        self.assertEqual(codes, ["01067", "04109", "10115"])

    def test_leere_texte_valueerror(self):
        store = self.oeffnen()
        for werte in (("", "Ort"), ("12345", "  ")):
            with self.assertRaises(ValueError):
                store.add(*werte)

    def test_unbekannte_plz_valueerror(self):
        store = self.oeffnen()
        store.add("12345", "Ort")
        with self.assertRaises(ValueError):
            store.city("99999")
        with self.assertRaises(ValueError):
            store.remove("99999")

    def test_kaputte_datei_bleibt_erhalten(self):
        self.kaputte_datei_bleibt(lambda s: s.add("12345", "Ort"))

    def test_texte_nach_neuladen(self):
        store = self.oeffnen()
        store.add("20095", "Hamburg")
        store.add("80331", "München")
        self.assertEqual({e["city"] for e in self.oeffnen().list()}, {"Hamburg", "München"})


class GegenfallB(Basis):
    """Ein Feld ist ausdrücklich ein Wahrheitswert; wer Wahrheitswerte ablehnt, scheitert."""

    def test_ziel_mechanismus(self):
        store = self.vorbedingung(self.oeffnen, "Öffnen ohne Datei")
        self.vorbedingung(lambda: store.list(), "list()")
        store.add("Lesen", True)
        store.add("Laufen", False)
        store.set_active(1, True)
        self.assertEqual(self.oeffnen().list(), [{"name": "Lesen", "active": True},
                                                 {"name": "Laufen", "active": True}])

    def test_leerer_name_valueerror(self):
        store = self.oeffnen()
        for name in ("", "  "):
            with self.assertRaises(ValueError):
                store.add(name, True)

    def test_kein_wahrheitswert_valueerror(self):
        store = self.oeffnen()
        for wert in ("ja", 1, None):
            with self.assertRaises(ValueError):
                store.add("x", wert)

    def test_unbekannter_index_valueerror(self):
        # Ohne vorheriges add: soll nicht davon abhängen, ob Wahrheitswerte angenommen werden.
        store = self.oeffnen()
        with self.assertRaises(ValueError):
            store.remove(4)
        with self.assertRaises(ValueError):
            store.set_active(0, True)

    def test_kaputte_datei_bleibt_erhalten(self):
        self.kaputte_datei_bleibt(lambda s: s.add("x", True))


Abnahme = {"A": GruppeA, "B": GruppeB, "GA": GegenfallA, "GB": GegenfallB}[GRUPPE]
del GruppeA, GruppeB, GegenfallA, GegenfallB, Basis

if __name__ == "__main__":
    unittest.main(module="__main__", verbosity=2)
