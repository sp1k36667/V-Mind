import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import Gemeinsam, starten  # noqa: E402


class Adapter:
    klasse = "NoteStore"
    cli_neu = ["add", "Zahnarzt anrufen", "termin"]
    cli_text = "Zahnarzt anrufen"
    leer = [lambda s: s.add("", ["a"]), lambda s: s.add("   ", ["a"])]

    @staticmethod
    def neu(store, n):
        return store.add(f"Notiz {n}", ["allgemein"])

    @staticmethod
    def aendern(store, eintrag):
        store.retag(eintrag, ["neu"])

    @staticmethod
    def geaendert(eintraege, eintrag):
        return any(e["id"] == eintrag and e["tags"] == ["neu"] for e in eintraege)


class Abnahme(Gemeinsam, unittest.TestCase):
    ADAPTER = Adapter

    def test_suche_ignoriert_schreibweise(self):
        store = self.oeffnen()
        treffer = store.add("Bericht", [" Arbeit ", "WICHTIG"])
        store.add("Urlaub", ["privat"])
        gefunden = store.search("arbeit")
        self.assertEqual([n["id"] for n in gefunden], [treffer])
        self.assertEqual(gefunden[0]["tags"], ["arbeit", "wichtig"])
        self.assertEqual([n["id"] for n in store.search("Wichtig")], [treffer])

    def test_leere_schlagwoerter_valueerror(self):
        store = self.oeffnen()
        with self.assertRaises(ValueError):
            store.add("Text", ["gut", "  "])
        eintrag = store.add("Text", [])
        with self.assertRaises(ValueError):
            store.retag(eintrag, [""])


if __name__ == "__main__":
    starten()
