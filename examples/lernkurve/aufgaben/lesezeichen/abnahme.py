import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import Gemeinsam, starten  # noqa: E402


class Adapter:
    klasse = "BookmarkStore"
    cli_neu = ["add", "https://python.org", "Python"]
    cli_text = "Python"
    leer = [
        lambda s: s.add("https://a.de", ""),
        lambda s: s.add("https://b.de", "   "),
    ]

    @staticmethod
    def neu(store, n):
        return store.add(f"https://seite{n}.de", f"Seite {n}")

    @staticmethod
    def aendern(store, eintrag):
        store.visit(eintrag)

    @staticmethod
    def geaendert(eintraege, eintrag):
        return any(e["id"] == eintrag and e["visits"] == 1 for e in eintraege)


class Abnahme(Gemeinsam, unittest.TestCase):
    ADAPTER = Adapter

    def test_ungueltige_url_valueerror(self):
        store = self.oeffnen()
        for url in ("ftp://a.de", "www.a.de", "https://", "http//a.de", ""):
            with self.assertRaises(ValueError, msg=url):
                store.add(url, "Titel")
        store.add("http://a.de", "Titel")

    def test_besuche_werden_gezaehlt(self):
        store = self.oeffnen()
        eintrag = store.add("https://a.de", "A")
        self.assertEqual(store.list()[0]["visits"], 0)
        store.visit(eintrag)
        self.oeffnen().visit(eintrag)
        self.assertEqual(self.oeffnen().list()[0]["visits"], 2)


if __name__ == "__main__":
    starten()
