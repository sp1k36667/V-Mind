import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import Gemeinsam, starten  # noqa: E402


class Adapter:
    klasse = "LoanList"
    cli_neu = ["lend", "Bohrmaschine", "Kim"]
    cli_text = "Bohrmaschine"
    leer = [lambda s: s.lend("", "Kim"), lambda s: s.lend("Buch", "   ")]

    @staticmethod
    def text(n):
        return f"Gegenstand {n}"

    @staticmethod
    def neu(store, n):
        return store.lend(f"Gegenstand {n}", f"Person {n}")

    @staticmethod
    def aendern(store, eintrag):
        store.give_back(eintrag)

    @staticmethod
    def geaendert(eintraege, eintrag):
        return any(e["id"] == eintrag and e["returned"] is True for e in eintraege)


class Abnahme(Gemeinsam, unittest.TestCase):
    ADAPTER = Adapter

    def test_doppelte_rueckgabe_valueerror(self):
        store = self.oeffnen()
        eintrag = store.lend("Leiter", "Sam")
        self.assertIs(store.list()[0]["returned"], False)
        store.give_back(eintrag)
        with self.assertRaises(ValueError):
            store.give_back(eintrag)


if __name__ == "__main__":
    starten()
