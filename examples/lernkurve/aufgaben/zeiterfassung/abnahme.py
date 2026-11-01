import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import Gemeinsam, starten  # noqa: E402


class Adapter:
    klasse = "TimeLog"
    cli_neu = ["add", "Webseite", "540", "600"]
    cli_text = "Webseite"
    leer = [lambda s: s.add("", 0, 10), lambda s: s.add("   ", 20, 30)]

    @staticmethod
    def neu(store, n):
        return store.add("Projekt", n * 100, n * 100 + 50)

    @staticmethod
    def aendern(store, eintrag):
        store.rename(eintrag, "Umbenannt")

    @staticmethod
    def geaendert(eintraege, eintrag):
        return any(e["id"] == eintrag and e["project"] == "Umbenannt" for e in eintraege)


class Abnahme(Gemeinsam, unittest.TestCase):
    ADAPTER = Adapter

    def test_ueberschneidung_valueerror(self):
        store = self.oeffnen()
        store.add("A", 60, 120)
        for start, end in ((90, 150), (30, 61), (60, 120), (0, 1440)):
            with self.assertRaises(ValueError, msg=f"{start}-{end}"):
                store.add("B", start, end)
        store.add("B", 120, 180)
        store.add("C", 0, 60)
        for start, end in ((10, 10), (50, 40), (-1, 5), (1400, 1441)):
            with self.assertRaises(ValueError, msg=f"{start}-{end}"):
                store.add("D", start, end)

    def test_summe_je_projekt(self):
        store = self.oeffnen()
        store.add("A", 0, 30)
        store.add("B", 30, 90)
        store.add("A", 100, 145)
        self.assertEqual(self.oeffnen().total("A"), 75)
        self.assertEqual(store.total("Z"), 0)
        self.assertEqual(self.cli("total", "B").stdout.strip(), "60")


if __name__ == "__main__":
    starten()
