import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import Gemeinsam, starten  # noqa: E402


class Adapter:
    klasse = "ShoppingList"
    cli_neu = ["add", "Brot", "2"]
    cli_text = "Brot"
    leer = [lambda s: s.add("", 1), lambda s: s.add("   ", 1)]

    @staticmethod
    def neu(store, n):
        return store.add(f"Artikel {n}", 1)

    @staticmethod
    def aendern(store, eintrag):
        store.set_qty(eintrag, 5)

    @staticmethod
    def geaendert(eintraege, eintrag):
        return any(e["id"] == eintrag and e["qty"] == 5 for e in eintraege)


class Abnahme(Gemeinsam, unittest.TestCase):
    ADAPTER = Adapter

    def test_gleicher_name_wird_zusammengefuehrt(self):
        store = self.oeffnen()
        erst = store.add("Milch", 1)
        zweit = store.add(" milch ", 2)
        self.assertEqual(erst, zweit)
        eintraege = self.oeffnen().list()
        self.assertEqual(len(eintraege), 1)
        self.assertEqual(eintraege[0]["qty"], 3)

    def test_ungueltige_mengen_valueerror(self):
        store = self.oeffnen()
        for menge in (0, -1):
            with self.assertRaises(ValueError):
                store.add("Eier", menge)
        eintrag = store.add("Eier", 6)
        with self.assertRaises(ValueError):
            store.set_qty(eintrag, 0)
        self.assertEqual(self.oeffnen().list()[0]["qty"], 6)


if __name__ == "__main__":
    starten()
