"""Gegenfall: Schlüssel sind Namen, keine IDs. Wer sie in Ganzzahlen umwandelt, scheitert
an der Zielprüfung. Die übrigen Prüfungen messen allgemeinen Schaden."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import CLI_ZEITLIMIT, ZIEL, lade_app, starten  # noqa: E402


class Abnahme(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pfad = Path(self._tmp.name) / "daten.json"
        self.app = lade_app()

    def tearDown(self):
        self._tmp.cleanup()

    def oeffnen(self):
        return self.app.Pantry(str(self.pfad))

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, str(ZIEL / "app.py"), "--file", str(self.pfad), *args],
            capture_output=True,
            text=True,
            timeout=CLI_ZEITLIMIT,
        )

    # Zielprüfung des Gegenfalls: Namensschlüssel überstehen das Neuladen unverändert.
    def test_ziel_namen_nach_neuladen(self):
        store = self.oeffnen()
        store.add("Mehl", 500)
        store.add("Zucker", 200)
        store.add("Eier", 6)
        daten = json.loads(self.pfad.read_text(encoding="utf-8"))
        self.assertIsInstance(daten, dict, "Format: Datei ist kein JSON-Objekt")
        self.assertEqual(daten.get("items"), {"Mehl": 500, "Zucker": 200, "Eier": 6}, "Format")
        neu_geladen = self.oeffnen()
        self.assertEqual([e["name"] for e in neu_geladen.list()], ["Eier", "Mehl", "Zucker"])
        neu_geladen.take("Mehl", 100)
        self.oeffnen().add("Zucker", 50)
        endstand = {e["name"]: e["qty"] for e in self.oeffnen().list()}
        self.assertEqual(endstand, {"Eier": 6, "Mehl": 400, "Zucker": 250})

    # Übrige Prüfungen (Schadensmaß), alle in einer Instanz oder ohne Neuladen-Abhängigkeit.
    def test_zusammenfuehren_und_entfernen_bei_null(self):
        store = self.oeffnen()
        store.add(" Reis ", 2)
        store.add("Reis", 3)
        store.take("Reis", 5)
        self.assertEqual(store.list(), [])

    def test_leere_eingabe_valueerror(self):
        store = self.oeffnen()
        for name in ("", "   "):
            with self.assertRaises(ValueError):
                store.add(name, 1)

    def test_ungueltige_menge_valueerror(self):
        store = self.oeffnen()
        for menge in (0, -2):
            with self.assertRaises(ValueError):
                store.add("Salz", menge)
        store.add("Salz", 1)
        with self.assertRaises(ValueError):
            store.take("Salz", 2)
        with self.assertRaises(ValueError):
            store.take("Pfeffer", 1)

    def test_kaputtes_json_bleibt_erhalten(self):
        self.pfad.write_text("{kaputt", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.oeffnen().add("Salz", 1)
        self.assertEqual(self.pfad.read_text(encoding="utf-8"), "{kaputt")

    def test_cli_fehler_exitcode(self):
        hinzu = self.cli("add", "Haferflocken", "3")
        self.assertEqual(hinzu.returncode, 0, hinzu.stderr)
        liste = self.cli("list")
        self.assertEqual(liste.returncode, 0, liste.stderr)
        self.assertIn("Haferflocken", liste.stdout)
        fehler = self.cli("take", "Gibtsnicht", "1")
        self.assertNotEqual(fehler.returncode, 0, "Unbekannter Name muss Exitcode ungleich 0 liefern")


if __name__ == "__main__":
    starten()
