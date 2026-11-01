import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import Gemeinsam, starten  # noqa: E402


class Adapter:
    klasse = "ContactBook"
    cli_neu = ["add", "Erika Muster", "erika@beispiel.de"]
    cli_text = "Erika Muster"
    leer = [lambda s: s.add("", "a@b.de"), lambda s: s.add("   ", "c@d.de")]

    @staticmethod
    def neu(store, n):
        return store.add(f"Person {n}", f"person{n}@beispiel.de")

    @staticmethod
    def aendern(store, eintrag):
        store.update_email(eintrag, "neu@beispiel.de")

    @staticmethod
    def geaendert(eintraege, eintrag):
        return any(e["id"] == eintrag and e["email"] == "neu@beispiel.de" for e in eintraege)


class Abnahme(Gemeinsam, unittest.TestCase):
    ADAPTER = Adapter

    def test_doppelte_email_valueerror(self):
        store = self.oeffnen()
        erst = store.add("Max", "max@beispiel.de")
        zweit = store.add("Moritz", "moritz@beispiel.de")
        with self.assertRaises(ValueError):
            store.add("Max Zwei", "MAX@Beispiel.de")
        with self.assertRaises(ValueError):
            store.update_email(zweit, "Max@beispiel.de")
        self.assertEqual([e["id"] for e in self.oeffnen().list()], [erst, zweit])

    def test_ungueltige_email_valueerror(self):
        store = self.oeffnen()
        for email in ("ohne-at", "a@b", "@beispiel.de", "a@@b.de", "a@b.", "  "):
            with self.assertRaises(ValueError, msg=email):
                store.add("Name", email)


if __name__ == "__main__":
    starten()
