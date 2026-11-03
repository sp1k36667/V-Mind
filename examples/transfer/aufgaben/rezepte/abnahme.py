import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import Gemeinsam, starten  # noqa: E402


class Adapter:
    klasse = "RecipeBook"
    cli_neu = ["add", "Linsensuppe", "40"]
    cli_text = "Linsensuppe"
    leer = [lambda s: s.add("", 10), lambda s: s.add("   ", 10)]

    @staticmethod
    def text(n):
        return f"Rezept {n}"

    @staticmethod
    def neu(store, n):
        return store.add(f"Rezept {n}", 10 + n)

    @staticmethod
    def aendern(store, eintrag):
        store.set_minutes(eintrag, 99)

    @staticmethod
    def geaendert(eintraege, eintrag):
        return any(e["id"] == eintrag and e["minutes"] == 99 for e in eintraege)


class Abnahme(Gemeinsam, unittest.TestCase):
    ADAPTER = Adapter

    def test_ungueltige_minuten_valueerror(self):
        store = self.oeffnen()
        for minuten in (0, -5):
            with self.assertRaises(ValueError):
                store.add("Tee", minuten)
        eintrag = store.add("Tee", 5)
        with self.assertRaises(ValueError):
            store.set_minutes(eintrag, 0)
        self.assertEqual(store.list()[0]["minutes"], 5)


if __name__ == "__main__":
    starten()
