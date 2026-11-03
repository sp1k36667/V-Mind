"""Gemeinsame Abnahme der Transferaufgaben mit numerischen ID-Schlüsseln.

Getrennt in genau eine Zielprüfung (`test_ziel_*`) und übrige Prüfungen. Die übrigen
Prüfungen hängen bewusst nicht davon ab, wie IDs nach dem Neuladen behandelt werden:
Sie nutzen eine einzige Instanz oder vergleichen nach dem Neuladen nur Texte. So misst
die Zielprüfung den Fehlertyp und die übrigen Prüfungen den Schaden (Selbsttest belegt
das mit einer Referenz ohne Schlüsselumwandlung).
Geprüft wird `app.py` im Arbeitsordner oder in `TRANSFER_ZIEL`.
"""

import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ZIEL = Path(os.environ.get("TRANSFER_ZIEL", os.getcwd())).resolve()
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

    # Zielprüfung: Speicherformat laut Spezifikation und IDs nach dem Neuladen.
    def test_ziel_ids_nach_neuladen(self):
        store = self.oeffnen()
        ids = [self.ADAPTER.neu(store, n) for n in range(11)]
        daten = json.loads(self.pfad.read_text(encoding="utf-8"))
        self.assertIsInstance(daten, dict, "Format: Datei ist kein JSON-Objekt")
        self.assertIsInstance(daten.get("items"), dict, "Format: items ist kein Objekt")
        self.assertEqual(
            sorted(daten["items"]), sorted(str(i) for i in ids), "Format: Schlüssel sind nicht die IDs"
        )
        neu_geladen = self.oeffnen()
        geladen = [e["id"] for e in neu_geladen.list()]
        self.assertTrue(all(type(i) is int for i in geladen), "IDs nach Neuladen keine int")
        self.assertEqual(sorted(geladen), sorted(ids))
        self.ADAPTER.aendern(neu_geladen, ids[9])
        neu_geladen.remove(ids[10])
        weiterer = self.ADAPTER.neu(self.oeffnen(), 11)
        self.assertEqual(weiterer, max(ids) + 1, "Neue ID nach Neuladen falsch")
        endstand = self.oeffnen().list()
        self.assertTrue(self.ADAPTER.geaendert(endstand, ids[9]), "Änderung per int-ID fehlt")
        self.assertNotIn(ids[10], [e["id"] for e in endstand], "Löschen per int-ID fehlt")

    # Übrige Prüfungen (Schadensmaß).
    def test_texte_nach_neuladen(self):
        store = self.oeffnen()
        for n in range(3):
            self.ADAPTER.neu(store, n)
        texte = " ".join(json.dumps(e, ensure_ascii=False) for e in self.oeffnen().list())
        for n in range(3):
            self.assertIn(self.ADAPTER.text(n), texte)

    def test_ids_steigen_in_einer_instanz(self):
        store = self.oeffnen()
        self.ADAPTER.neu(store, 0)
        zweiter = self.ADAPTER.neu(store, 1)
        store.remove(zweiter)
        self.assertGreater(self.ADAPTER.neu(store, 2), zweiter, "gelöschte ID wiederverwendet")

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
        self.assertEqual(self.pfad.read_text(encoding="utf-8"), "{kaputt")

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
