import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import Gemeinsam, starten  # noqa: E402


class Adapter:
    klasse = "ExpenseLog"
    cli_neu = ["add", "Fahrkarte", "290"]
    cli_text = "Fahrkarte"
    leer = [lambda s: s.add("", 100), lambda s: s.add("   ", 100)]

    @staticmethod
    def text(n):
        return f"Ausgabe {n}"

    @staticmethod
    def neu(store, n):
        return store.add(f"Ausgabe {n}", 100 + n)

    @staticmethod
    def aendern(store, eintrag):
        store.set_cents(eintrag, 4242)

    @staticmethod
    def geaendert(eintraege, eintrag):
        return any(e["id"] == eintrag and e["cents"] == 4242 for e in eintraege)


class Abnahme(Gemeinsam, unittest.TestCase):
    ADAPTER = Adapter

    def test_summe_nach_aenderung_und_loeschen(self):
        store = self.oeffnen()
        erst = store.add("Brot", 250)
        zweit = store.add("Kaffee", 300)
        store.add("Zeitung", 120)
        store.set_cents(erst, 200)
        store.remove(zweit)
        self.assertEqual(store.total(), 320)
        with self.assertRaises(ValueError):
            store.add("Nichts", 0)


if __name__ == "__main__":
    starten()
