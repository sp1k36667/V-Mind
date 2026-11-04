"""Abnahme der Aufgabensuche für Transfer v3. Liest `aufgabe.json` neben dieser Datei und prüft
`app.py` im Arbeitsordner (oder in `TRANSFER_ZIEL`).

Je Aufgabe genau eine Zielprüfung `test_ziel_mechanismus`. Scheitert sie, bevor der
Mechanismus erreicht ist (App nicht ladbar, Symbol fehlt, vorbereitende Schritte scheitern),
lautet die Meldung „Vorbedingung: …“; der Mechanismus war dann nicht beobachtbar.
`test_diag_*` ist eine Diagnose und zählt weder zum Ziel noch zu den übrigen Prüfungen. Alle
anderen `test_*` sind übrige Prüfungen; sie hängen nicht von der jeweiligen Falle ab.
"""

import datetime
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ZIEL = Path(os.environ.get("TRANSFER_ZIEL", os.getcwd())).resolve()
AUFGABE = json.loads((Path(__file__).resolve().parent / "aufgabe.json").read_text(encoding="utf-8"))
NAME, SYMBOL = AUFGABE["name"], AUFGABE["symbol"]


class Basis(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pfad = Path(self._tmp.name) / "daten.json"
        self.app_fehler = None
        try:
            if str(ZIEL) not in sys.path:
                sys.path.insert(0, str(ZIEL))
            self.app = importlib.import_module("app")
            getattr(self.app, SYMBOL)
        except Exception as fehler:  # noqa: BLE001 - jede Ladefehlerart ist Vorbedingung
            self.app_fehler = fehler

    def tearDown(self):
        self._tmp.cleanup()

    def neu(self, *argumente):
        """Symbol aus app.py (Klasse instanziiert oder Funktion)."""
        if self.app_fehler:
            raise self.app_fehler
        objekt = getattr(self.app, SYMBOL)
        return objekt(*argumente) if isinstance(objekt, type) else objekt

    def vorbedingung(self, aufruf, beschreibung):
        """Führt einen Schritt vor dem Mechanismus aus; Fehler heißen „nicht beobachtbar“."""
        try:
            return aufruf()
        except Exception as fehler:  # noqa: BLE001
            self.fail(f"Vorbedingung: {beschreibung}: {type(fehler).__name__}: {fehler}")

    def pruefe_vorbedingung(self, bedingung, beschreibung):
        if not bedingung:
            self.fail(f"Vorbedingung: {beschreibung}")


class Datumsimport(Basis):
    """Falle: datetime.strptime akzeptiert Monat und Tag ohne führende Null."""

    def test_ziel_mechanismus(self):
        parse = self.vorbedingung(self.neu, "parse_date laden")
        ergebnis = self.vorbedingung(lambda: parse("2026-01-05"), 'parse_date("2026-01-05")')
        self.pruefe_vorbedingung(ergebnis == datetime.date(2026, 1, 5),
                                 f'parse_date("2026-01-05") liefert {ergebnis!r}')
        for text in ("2026-1-5", "2026-01-5", "2026-1-05"):
            with self.assertRaises(ValueError, msg=f"{text!r} ohne führende Null angenommen"):
                parse(text)

    def test_diag_kompaktformat_abgelehnt(self):
        # date.fromisoformat nimmt ab Python 3.11 auch "20260105" an.
        with self.assertRaises(ValueError):
            self.neu()("20260105")

    def test_gueltige_daten(self):
        parse = self.neu()
        for text, erwartet in (("2024-02-29", (2024, 2, 29)), ("1999-12-31", (1999, 12, 31)),
                               ("2026-10-01", (2026, 10, 1))):
            ergebnis = parse(text)
            self.assertEqual(ergebnis, datetime.date(*erwartet))
            self.assertIs(type(ergebnis), datetime.date)

    def test_ungueltiger_kalendertag_valueerror(self):
        for text in ("2026-02-30", "2023-02-29", "2026-13-01", "2026-00-10", "2026-04-31"):
            with self.assertRaises(ValueError):
                self.neu()(text)

    def test_falsches_format_valueerror(self):
        for text in ("", " 2026-01-05", "2026-01-05 ", "05.01.2026", "2026/01/05", "2026-01"):
            with self.assertRaises(ValueError):
                self.neu()(text)

    def test_kein_text_valueerror(self):
        for wert in (None, 20260105, datetime.date(2026, 1, 5)):
            with self.assertRaises(ValueError):
                self.neu()(wert)


class Kalender(Basis):
    """Falle: Vergleich mit <= statt < macht angrenzende Zeiträume zu Überschneidungen."""

    def test_ziel_mechanismus(self):
        kalender = self.vorbedingung(self.neu, "Calendar()")
        erste = self.vorbedingung(lambda: kalender.reserve(60, 120), "reserve(60, 120)")
        self.pruefe_vorbedingung(erste is True, f"reserve(60, 120) liefert {erste!r}")
        liste = self.vorbedingung(kalender.bookings, "bookings()")
        self.pruefe_vorbedingung([tuple(b) for b in liste] == [(60, 120)],
                                 f"bookings() liefert {liste!r}")
        self.assertIs(kalender.reserve(120, 180), True, "angrenzend danach abgelehnt")
        self.assertIs(kalender.reserve(0, 60), True, "angrenzend davor abgelehnt")
        self.assertEqual([tuple(b) for b in kalender.bookings()], [(0, 60), (60, 120), (120, 180)])

    def test_ueberschneidungen_abgelehnt(self):
        kalender = self.neu()
        self.assertIs(kalender.reserve(600, 700), True)
        for start, ende in ((650, 750), (550, 650), (500, 800), (620, 680), (600, 700)):
            self.assertIs(kalender.reserve(start, ende), False, f"{start}-{ende} angenommen")
        self.assertEqual([tuple(b) for b in kalender.bookings()], [(600, 700)])

    def test_sortiert(self):
        kalender = self.neu()
        for start, ende in ((900, 960), (300, 360), (600, 630)):
            self.assertIs(kalender.reserve(start, ende), True)
        self.assertEqual([tuple(b) for b in kalender.bookings()],
                         [(300, 360), (600, 630), (900, 960)])

    def test_ungueltige_zeiten_valueerror(self):
        kalender = self.neu()
        for start, ende in ((100, 100), (120, 60), (-1, 10), (1400, 1441), (1.5, 10), ("1", 10)):
            with self.assertRaises(ValueError):
                kalender.reserve(start, ende)
        self.assertEqual(list(kalender.bookings()), [])

    def test_ganzer_tag(self):
        kalender = self.neu()
        self.assertIs(kalender.reserve(0, 1440), True)
        self.assertIs(kalender.reserve(700, 710), False)


class Warteliste(Basis):
    """Falle: erneutes Stornieren derselben ID wird nicht erkannt (still angenommen oder
    verändert den Stand)."""

    def test_ziel_mechanismus(self):
        kurs = self.vorbedingung(lambda: self.neu(2), "Waitlist(2)")
        ids = self.vorbedingung(lambda: [kurs.book(n) for n in ("Anna", "Ben", "Cem", "Dana")],
                                "vier Buchungen")
        self.vorbedingung(lambda: kurs.cancel(ids[0]), "erste Stornierung")
        stand = self.vorbedingung(lambda: (kurs.confirmed(), kurs.waiting()), "confirmed/waiting")
        self.pruefe_vorbedingung(stand == (["Ben", "Cem"], ["Dana"]),
                                 f"Nachrücken nach erster Stornierung falsch: {stand!r}")
        with self.assertRaises(ValueError, msg="zweite Stornierung derselben ID angenommen"):
            kurs.cancel(ids[0])
        self.assertEqual((kurs.confirmed(), kurs.waiting()), (["Ben", "Cem"], ["Dana"]),
                         "zweite Stornierung hat den Stand verändert")

    def test_ids_und_reihenfolge(self):
        kurs = self.neu(1)
        ids = [kurs.book(n) for n in ("Eva", "Finn", "Gül")]
        self.assertTrue(all(type(i) is int for i in ids))
        self.assertEqual(len(set(ids)), 3)
        self.assertEqual(kurs.confirmed(), ["Eva"])
        self.assertEqual(kurs.waiting(), ["Finn", "Gül"])

    def test_wartende_stornieren(self):
        kurs = self.neu(1)
        ids = [kurs.book(n) for n in ("Eva", "Finn", "Gül")]
        kurs.cancel(ids[1])
        self.assertEqual(kurs.confirmed(), ["Eva"])
        self.assertEqual(kurs.waiting(), ["Gül"])

    def test_nachruecken(self):
        kurs = self.neu(2)
        ids = [kurs.book(n) for n in ("Eva", "Finn", "Gül", "Hans")]
        kurs.cancel(ids[1])
        self.assertEqual(kurs.confirmed(), ["Eva", "Gül"])
        self.assertEqual(kurs.waiting(), ["Hans"])

    def test_unbekannte_id_valueerror(self):
        kurs = self.neu(2)
        kurs.book("Eva")
        with self.assertRaises(ValueError):
            kurs.cancel(999)
        self.assertEqual(kurs.confirmed(), ["Eva"])

    def test_ungueltige_werte_valueerror(self):
        for kapazitaet in (0, -1, 1.5):
            with self.assertRaises(ValueError):
                self.neu(kapazitaet)
        kurs = self.neu(1)
        for name in ("", "   "):
            with self.assertRaises(ValueError):
                kurs.book(name)


class Paketstatus(Basis):
    """Falle: ein verspätetes Ereignis stuft den Status zurück."""

    def test_ziel_mechanismus(self):
        paket = self.vorbedingung(self.neu, "Package()")
        self.vorbedingung(lambda: paket.apply("in_transit"), 'apply("in_transit")')
        self.vorbedingung(lambda: paket.apply("delivered"), 'apply("delivered")')
        stand = self.vorbedingung(paket.status, "status()")
        self.pruefe_vorbedingung(stand == "delivered", f"status() nach delivered: {stand!r}")
        paket.apply("in_transit")
        self.assertEqual(paket.status(), "delivered", "verspätetes in_transit stuft zurück")
        paket.apply("created")
        self.assertEqual(paket.status(), "delivered", "verspätetes created stuft zurück")

    def test_anfangsstatus(self):
        self.assertEqual(self.neu().status(), "created")

    def test_reihenfolge_vorwaerts(self):
        paket = self.neu()
        for status in ("in_transit", "out_for_delivery", "delivered"):
            paket.apply(status)
            self.assertEqual(paket.status(), status)

    def test_ueberspringen(self):
        paket = self.neu()
        paket.apply("out_for_delivery")
        self.assertEqual(paket.status(), "out_for_delivery")

    def test_gleiches_ereignis_zweimal(self):
        paket = self.neu()
        paket.apply("in_transit")
        paket.apply("in_transit")
        self.assertEqual(paket.status(), "in_transit")

    def test_unbekanntes_ereignis_valueerror(self):
        paket = self.neu()
        paket.apply("in_transit")
        for wert in ("lost", "", "Delivered", None, 3):
            with self.assertRaises(ValueError):
                paket.apply(wert)
        self.assertEqual(paket.status(), "in_transit")


class Bestellimport(Basis):
    """Falle: verarbeitete IDs nur im Speicher; nach Neuinstanziierung wird doppelt gezählt."""

    def oeffnen(self):
        return self.neu(str(self.pfad))

    def test_ziel_mechanismus(self):
        erster = self.vorbedingung(self.oeffnen, "Importer(path)")
        gezaehlt = self.vorbedingung(lambda: erster.ingest("e-1", 500), 'ingest("e-1", 500)')
        self.pruefe_vorbedingung(gezaehlt is True, f'ingest("e-1", 500) liefert {gezaehlt!r}')
        summe = self.vorbedingung(lambda: self.oeffnen().total(), "total() nach Neuöffnen")
        self.pruefe_vorbedingung(summe == 500, f"Summe nach Neuöffnen {summe!r} statt 500")
        zweiter = self.oeffnen()
        self.assertIs(zweiter.ingest("e-1", 500), False, "doppelte ID nach Neuöffnen gezählt")
        self.assertEqual(zweiter.total(), 500)
        self.assertEqual(self.oeffnen().total(), 500)

    def test_anfangs_null(self):
        self.assertEqual(self.oeffnen().total(), 0)

    def test_duplikat_in_derselben_instanz(self):
        importer = self.oeffnen()
        self.assertIs(importer.ingest("a", 100), True)
        self.assertIs(importer.ingest("a", 100), False)
        self.assertIs(importer.ingest("b", 250), True)
        self.assertEqual(importer.total(), 350)

    def test_summe_dauerhaft(self):
        importer = self.oeffnen()
        importer.ingest("a", 100)
        importer.ingest("b", 200)
        neu = self.oeffnen()
        self.assertEqual(neu.total(), 300)
        self.assertIs(neu.ingest("c", 50), True)
        self.assertEqual(self.oeffnen().total(), 350)

    def test_ungueltige_werte_valueerror(self):
        importer = self.oeffnen()
        for event_id, cents in (("", 100), ("   ", 100), (None, 100), ("x", 0), ("x", -5),
                                ("x", 1.5), ("x", "100")):
            with self.assertRaises(ValueError):
                importer.ingest(event_id, cents)
        self.assertEqual(importer.total(), 0)


class Lager(Basis):
    """Falle: der Bestand wird vor der Prüfung verringert."""

    def test_ziel_mechanismus(self):
        lager = self.vorbedingung(lambda: self.neu(5), "Stock(5)")
        self.vorbedingung(lambda: lager.withdraw(3), "withdraw(3)")
        stand = self.vorbedingung(lager.balance, "balance()")
        self.pruefe_vorbedingung(stand == 2, f"balance() nach withdraw(3): {stand!r}")
        with self.assertRaises(ValueError, msg="zu große Entnahme angenommen"):
            lager.withdraw(4)
        self.assertEqual(lager.balance(), 2, "abgelehnte Entnahme hat den Bestand verändert")

    def test_einlagern(self):
        lager = self.neu(0)
        lager.deposit(4)
        lager.deposit(1)
        self.assertEqual(lager.balance(), 5)

    def test_bis_null_entnehmen(self):
        lager = self.neu(3)
        lager.withdraw(3)
        self.assertEqual(lager.balance(), 0)

    def test_ungueltige_mengen_valueerror(self):
        lager = self.neu(5)
        for menge in (0, -1, 1.5, "2"):
            with self.assertRaises(ValueError):
                lager.deposit(menge)
            with self.assertRaises(ValueError):
                lager.withdraw(menge)
        self.assertEqual(lager.balance(), 5)

    def test_ungueltiger_anfangsbestand_valueerror(self):
        for wert in (-1, 2.5, "3"):
            with self.assertRaises(ValueError):
                self.neu(wert)


Abnahme = {"datumsimport": Datumsimport, "kalender": Kalender, "warteliste": Warteliste,
           "paketstatus": Paketstatus, "bestellimport": Bestellimport, "lager": Lager}[NAME]
del Datumsimport, Kalender, Warteliste, Paketstatus, Bestellimport, Lager, Basis

if __name__ == "__main__":
    unittest.main(module="__main__", verbosity=2)
