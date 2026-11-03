import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import Gemeinsam, starten  # noqa: E402


class Adapter:
    klasse = "Calendar"
    cli_neu = ["add", "Zahnarzt", "2026-12-01"]
    cli_text = "Zahnarzt"
    leer = [lambda s: s.add("", "2026-01-01"), lambda s: s.add("   ", "2026-01-01")]

    @staticmethod
    def text(n):
        return f"Termin {n}"

    @staticmethod
    def neu(store, n):
        return store.add(f"Termin {n}", f"2026-03-{n + 1:02d}")

    @staticmethod
    def aendern(store, eintrag):
        store.move(eintrag, "2027-07-07")

    @staticmethod
    def geaendert(eintraege, eintrag):
        return any(e["id"] == eintrag and e["date"] == "2027-07-07" for e in eintraege)


class Abnahme(Gemeinsam, unittest.TestCase):
    ADAPTER = Adapter

    def test_sortierung_und_ungueltiges_datum(self):
        store = self.oeffnen()
        spaet = store.add("Spät", "2026-05-02")
        frueh = store.add("Früh", "2026-05-01")
        gleich = store.add("Gleich", "2026-05-02")
        self.assertEqual([e["id"] for e in store.list()], [frueh, spaet, gleich])
        for datum in ("2026-02-30", "01.05.2026", "morgen"):
            with self.assertRaises(ValueError):
                store.add("Falsch", datum)


if __name__ == "__main__":
    starten()
