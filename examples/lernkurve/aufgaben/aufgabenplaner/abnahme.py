import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import Gemeinsam, starten  # noqa: E402


class Adapter:
    klasse = "TaskStore"
    cli_neu = ["add", "Milch kaufen"]
    cli_text = "Milch kaufen"
    leer = [lambda s: s.add(""), lambda s: s.add("   ")]

    @staticmethod
    def neu(store, n):
        return store.add(f"Aufgabe {n}")

    @staticmethod
    def aendern(store, eintrag):
        store.done(eintrag)

    @staticmethod
    def geaendert(eintraege, eintrag):
        return any(e["id"] == eintrag and e["done"] is True for e in eintraege)


class Abnahme(Gemeinsam, unittest.TestCase):
    ADAPTER = Adapter

    def test_neue_aufgabe_ist_offen(self):
        store = self.oeffnen()
        eintrag = store.add("Lesen")
        self.assertEqual(store.list(), [{"id": eintrag, "text": "Lesen", "done": False}])

    def test_cli_zeigt_status(self):
        self.cli("add", "Lesen")
        self.cli("add", "Schreiben")
        self.assertEqual(self.cli("done", "1").returncode, 0)
        zeilen = self.cli("list").stdout.splitlines()
        self.assertIn("1 [x] Lesen", zeilen)
        self.assertIn("2 [ ] Schreiben", zeilen)


if __name__ == "__main__":
    starten()
