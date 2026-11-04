#!/usr/bin/env python3
"""Regeln, Zeitplan, Prompts und Host-Schutz der Aufgabensuche mit erfundenen Daten, ohne Modell."""

import json
import tempfile
import unittest
from pathlib import Path

import aufgaben
import auswerten
import run
from werkzeuge import BASIS, plan_laden, tests, zeitplan

PLAN = plan_laden()


def ergebnis(lauf, ziel="bestanden", uebrige=None, technisch=False):
    von = len(tests(lauf["aufgabe"])["uebrige"])
    return {**lauf, "zielstatus": "nicht_beobachtbar" if technisch else ziel,
            "uebrige_ok": 0 if technisch else (von if uebrige is None else uebrige),
            "uebrige_von": von, "technischer_fehler": "URLError" if technisch else None}


def o_daten(regel):
    """regel(lauf, index_des_seeds) -> dict mit Argumenten für ergebnis()"""
    seeds = PLAN["stufen"]["o"]["seeds"]
    return [ergebnis(l, **regel(l, seeds.index(l["seed"]))) for l in zeitplan("o", PLAN)]


def o_bericht(regel, commit="abc"):
    return auswerten.o_auswerten({"stufe": "o", "commit": commit, "attrappe": False},
                                 o_daten(regel), PLAN)


class Zeitplan(unittest.TestCase):
    def test_o_vollstaendig_und_wiederholbar(self):
        laeufe = zeitplan("o", PLAN)
        self.assertEqual(laeufe, zeitplan("o", PLAN))
        self.assertEqual(len(laeufe), 12)
        self.assertEqual(sorted((l["aufgabe"], l["seed"]) for l in laeufe),
                         sorted((n, s) for n in aufgaben.REIHENFOLGE for s in (3001, 3002)))
        self.assertTrue(all(l["bedingung"] == "O" for l in laeufe))

    def test_d_hoechstens_drei_mit_festem_seed(self):
        laeufe = zeitplan("d", PLAN, ["lager", "kalender"])
        self.assertEqual([(l["aufgabe"], l["seed"], l["nr"]) for l in laeufe],
                         [("lager", 3101, 1), ("kalender", 3101, 2)])
        with self.assertRaises(ValueError):
            zeitplan("d", PLAN, aufgaben.REIHENFOLGE[:4])
        with self.assertRaises(ValueError):
            zeitplan("d", PLAN)

    def test_grenze_passt_zu_den_stufen(self):
        self.assertEqual(len(zeitplan("o", PLAN)) + PLAN["regel"]["d_hoechstens"],
                         PLAN["regel"]["max_aufrufe"])

    def test_seeds_getrennt_von_v2(self):
        v2 = json.loads((BASIS.parent / "transfer-v2" / "bedingungen.json").read_text(encoding="utf-8"))
        alt = {s for st in v2["stufen"].values() for s in st["seeds"]}
        neu = {*PLAN["stufen"]["o"]["seeds"], PLAN["stufen"]["d"]["seed"]}
        self.assertFalse(alt & neu)
        self.assertEqual(len(neu), 3)


class Prompt(unittest.TestCase):
    def test_direkte_hilfe_nur_unter_d(self):
        for name in aufgaben.REIHENFOLGE:
            hilfe = PLAN["direkte_anweisung"][name]
            o = json.loads(run.prompt(name, "O", PLAN))
            d = json.loads(run.prompt(name, "D", PLAN))
            self.assertNotIn(hilfe, o["aufgabe"])
            self.assertTrue(d["aufgabe"].endswith(hilfe))
            self.assertEqual(o["geruest"], aufgaben.geruest(name))
            self.assertNotIn("gedaechtnis", o)

    def test_geruest_ohne_loesungslogik(self):
        for name in aufgaben.REIHENFOLGE:
            geruest = aufgaben.geruest(name)
            self.assertIn(aufgaben.symbol(name), geruest)
            koerper = [z.strip() for z in geruest.splitlines()
                       if z.startswith("        ") and not z.strip().startswith('"""')]
            self.assertTrue(all(z == "raise NotImplementedError" for z in koerper), name)


class Regel(unittest.TestCase):
    def test_gemischt_vor_nur_verfehlt_und_feste_reihenfolge(self):
        gemischt = {"warteliste", "lager"}

        def regel(lauf, i):
            if lauf["aufgabe"] in gemischt:
                return {"ziel": "bestanden" if i == 0 else "verfehlt"}
            return {"ziel": "verfehlt"}
        bericht = o_bericht(regel)
        self.assertTrue(bericht["gueltig"])
        self.assertEqual(bericht["rang"], ["warteliste", "lager", "datumsimport", "kalender",
                                           "paketstatus", "bestellimport"])
        self.assertEqual(bericht["auswahl"], ["warteliste", "lager", "datumsimport"])

    def test_ohne_beobachteten_fehler_nicht_geeignet(self):
        def regel(lauf, i):
            return {"datumsimport": {"ziel": "bestanden"},
                    "kalender": {"ziel": "bestanden" if i == 0 else "nicht_beobachtbar"},
                    "warteliste": {"ziel": "nicht_beobachtbar"}}.get(lauf["aufgabe"], {"ziel": "verfehlt"})
        k = o_bericht(regel)["kandidaten"]
        self.assertFalse(k["datumsimport"]["geeignet"])
        self.assertFalse(k["kalender"]["geeignet"])
        self.assertFalse(k["warteliste"]["geeignet"])
        self.assertTrue(k["paketstatus"]["geeignet"])

    def test_technischer_ausfall_schliesst_aus(self):
        def regel(lauf, i):
            if lauf["aufgabe"] == "kalender" and i == 1:
                return {"technisch": True}
            return {"ziel": "verfehlt"}
        bericht = o_bericht(regel)
        self.assertFalse(bericht["kandidaten"]["kalender"]["geeignet"])
        self.assertNotIn("kalender", bericht["rang"])

    def test_uebrige_nenner_beide_laeufe(self):
        # warteliste: 5 übrige je Lauf, Nenner 10; 8/10 reicht, 7/10 nicht.
        for ok, erwartet in ((8, True), (7, False)):
            def regel(lauf, i, ok=ok):
                if lauf["aufgabe"] == "warteliste":
                    return {"ziel": "verfehlt", "uebrige": 5 if i == 0 else ok - 5}
                return {"ziel": "verfehlt"}
            k = o_bericht(regel)["kandidaten"]["warteliste"]
            self.assertEqual((k["uebrige_von"], k["geeignet"]), (10, erwartet))

    def test_nicht_beobachtbar_zaehlt_im_nenner(self):
        def regel(lauf, i):
            if lauf["aufgabe"] == "lager":
                return {"ziel": "verfehlt"} if i == 0 else {"ziel": "nicht_beobachtbar", "uebrige": 0}
            return {"ziel": "verfehlt"}
        k = o_bericht(regel)["kandidaten"]["lager"]
        self.assertEqual((k["uebrige_ok"], k["uebrige_von"], k["geeignet"]), (4, 8, False))

    def test_fehlender_lauf_macht_ungueltig_ohne_auswahl(self):
        daten = o_daten(lambda l, i: {"ziel": "verfehlt"})[1:]
        bericht = auswerten.o_auswerten({"stufe": "o", "commit": "abc", "attrappe": False}, daten, PLAN)
        self.assertFalse(bericht["gueltig"])
        self.assertEqual(bericht["auswahl"], [])

    def test_d_bestaetigt_nur_mit_ziel_und_uebrigen(self):
        o = o_bericht(lambda l, i: {"ziel": "verfehlt"})
        laeufe = zeitplan("d", PLAN, o["auswahl"])
        daten = [ergebnis(laeufe[0]), ergebnis(laeufe[1], "verfehlt"), ergebnis(laeufe[2], uebrige=1)]
        d = auswerten.d_auswerten(o, {"stufe": "d", "commit": "abc", "auswahl": o["auswahl"]}, daten, PLAN)
        self.assertTrue(d["gueltig"])
        self.assertEqual(d["bestaetigt"], [laeufe[0]["aufgabe"]])

    def test_d_anderer_commit_oder_auswahl_ungueltig(self):
        o = o_bericht(lambda l, i: {"ziel": "verfehlt"})
        daten = [ergebnis(l) for l in zeitplan("d", PLAN, o["auswahl"])]
        for einstellungen in ({"stufe": "d", "commit": "xyz", "auswahl": o["auswahl"]},
                              {"stufe": "d", "commit": "abc", "auswahl": o["auswahl"][::-1]}):
            d = auswerten.d_auswerten(o, einstellungen, daten, PLAN)
            self.assertFalse(d["gueltig"])
            self.assertEqual(d["bestaetigt"], [])


class Fehlerquelle:
    """Jede Anfrage scheitert wie ein nicht erreichbarer Server."""

    @staticmethod
    def anfrage_bauen(lauf, plan):
        return {"test": True}

    @staticmethod
    def senden(nutzlast, lauf):
        raise OSError("Verbindung abgelehnt")


class Host(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.wurzel = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def ausfuehren(self, stufe, quelle=run.Attrappe, commit="abc"):
        run.stufe_ausfuehren(self.wurzel, stufe, PLAN, quelle, commit, True, True)

    def protokoll(self):
        return run.protokoll_lesen(self.wurzel)

    def test_beide_stufen_genau_fuenfzehn_aufrufe(self):
        self.ausfuehren("o")
        self.ausfuehren("d")
        self.assertEqual(len(self.protokoll()), 15)
        self.ausfuehren("o")
        self.ausfuehren("d")
        self.assertEqual(len(self.protokoll()), 15, "erneuter Start darf nichts senden")

    def test_fehlgeschlagene_anfragen_zaehlen(self):
        self.ausfuehren("o", Fehlerquelle)
        self.assertEqual(len(self.protokoll()), 12)
        ergebnisse = auswerten.laden(self.wurzel / "o")[1]
        self.assertTrue(all(e["technischer_fehler"] for e in ergebnisse))

    def test_grenze_verweigert_weitere_anfrage(self):
        lauf = {"aufgabe": "lager", "bedingung": "D", "seed": 3101, "nr": 99}
        with (self.wurzel / run.PROTOKOLL).open("w", encoding="utf-8") as datei:
            for i in range(PLAN["regel"]["max_aufrufe"]):
                datei.write(json.dumps({"stufe": "o", "nr": i + 1}) + "\n")
        with self.assertRaises(SystemExit):
            run.aufruf_anmelden(self.wurzel, "d", lauf, PLAN)

    def test_derselbe_lauf_nie_zweimal(self):
        lauf = {"aufgabe": "lager", "bedingung": "O", "seed": 3001, "nr": 1}
        run.aufruf_anmelden(self.wurzel, "o", lauf, PLAN)
        with self.assertRaises(SystemExit):
            run.aufruf_anmelden(self.wurzel, "o", lauf, PLAN)

    def test_unvollstaendiger_laufordner_stoppt(self):
        erster = zeitplan("o", PLAN)[0]
        ordner = self.wurzel / "o" / f"01-{erster['aufgabe']}-O-s{erster['seed']}"
        ordner.mkdir(parents=True)
        with self.assertRaises(SystemExit):
            self.ausfuehren("o")
        self.assertEqual(self.protokoll(), [])

    def test_d_nur_nach_gueltiger_o_desselben_commits(self):
        with self.assertRaises((SystemExit, FileNotFoundError)):
            self.ausfuehren("d")
        self.ausfuehren("o", commit="abc")
        with self.assertRaises(SystemExit):
            self.ausfuehren("d", commit="anders")


if __name__ == "__main__":
    unittest.main(verbosity=1)
