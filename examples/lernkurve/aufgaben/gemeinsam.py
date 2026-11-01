"""Gemeinsame Abnahmeprüfungen der Lernkurve: sieben Fallstricke, für alle Aufgaben gleich.

Jede Aufgabe liefert in ihrer `abnahme.py` einen Adapter. Geprüft wird die Datei `app.py`
im aktuellen Arbeitsordner (oder in `LERNKURVE_ZIEL`).
"""

import importlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ZIEL = Path(os.environ.get("LERNKURVE_ZIEL", os.getcwd())).resolve()
CLI_ZEITLIMIT = 20
UNBEKANNTE_ID = 999


def lade_app():
    if str(ZIEL) not in sys.path:
        sys.path.insert(0, str(ZIEL))
    return importlib.import_module("app")


class Gemeinsam:
    """Mixin für `unittest.TestCase`; Unterklassen setzen `ADAPTER`."""

    ADAPTER = None

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pfad = Path(self._tmp.name) / "daten.json"
        self.app = lade_app()

    def tearDown(self):
        self._tmp.cleanup()

    def oeffnen(self):
        return getattr(self.app, self.ADAPTER.klasse)(str(self.pfad))

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, str(ZIEL / "app.py"), "--file", str(self.pfad), *args],
            capture_output=True,
            text=True,
            timeout=CLI_ZEITLIMIT,
        )

    def test_persistenz_nach_wiederoeffnen(self):
        eintrag = self.ADAPTER.neu(self.oeffnen(), 0)
        self.assertTrue(self.pfad.exists(), "Datei wurde nicht am übergebenen Pfad angelegt")
        ids = [e["id"] for e in self.oeffnen().list()]
        self.assertIn(eintrag, ids)

    def test_ids_steigen_nach_loeschen(self):
        store = self.oeffnen()
        self.ADAPTER.neu(store, 0)
        zweiter = self.ADAPTER.neu(store, 1)
        store.remove(zweiter)
        dritter = self.ADAPTER.neu(self.oeffnen(), 2)
        self.assertGreater(dritter, zweiter, "ID eines gelöschten Eintrags wurde wiederverwendet")

    def test_leere_eingabe_valueerror(self):
        store = self.oeffnen()
        for aufruf in self.ADAPTER.leer:
            with self.assertRaises(ValueError):
                aufruf(store)

    def test_unbekannte_id_valueerror(self):
        store = self.oeffnen()
        self.ADAPTER.neu(store, 0)
        with self.assertRaises(ValueError):
            store.remove(UNBEKANNTE_ID)
        with self.assertRaises(ValueError):
            self.ADAPTER.aendern(store, UNBEKANNTE_ID)

    def test_kaputtes_json_bleibt_erhalten(self):
        self.pfad.write_text("{kaputt", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.ADAPTER.neu(self.oeffnen(), 0)
        self.assertEqual(
            self.pfad.read_text(encoding="utf-8"),
            "{kaputt",
            "Beschädigte Datei wurde verändert",
        )

    def test_aenderung_sofort_gespeichert(self):
        store = self.oeffnen()
        eintrag = self.ADAPTER.neu(store, 0)
        weg = self.ADAPTER.neu(store, 1)
        self.ADAPTER.aendern(store, eintrag)
        store.remove(weg)
        neu_geladen = self.oeffnen().list()
        self.assertTrue(
            self.ADAPTER.geaendert(neu_geladen, eintrag), "Änderung nach Neuöffnen nicht vorhanden"
        )
        self.assertNotIn(weg, [e["id"] for e in neu_geladen], "Löschen nicht gespeichert")

    def test_cli_fehler_exitcode(self):
        hinzu = self.cli(*self.ADAPTER.cli_neu)
        self.assertEqual(hinzu.returncode, 0, hinzu.stderr)
        liste = self.cli("list")
        self.assertEqual(liste.returncode, 0, liste.stderr)
        self.assertIn(self.ADAPTER.cli_text, liste.stdout)
        fehler = self.cli("remove", str(UNBEKANNTE_ID))
        self.assertNotEqual(fehler.returncode, 0, "Unbekannte ID muss Exitcode ungleich 0 liefern")


def starten():
    unittest.main(module="__main__", verbosity=2)
