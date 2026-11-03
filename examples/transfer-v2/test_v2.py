#!/usr/bin/env python3
"""Regeln, Zeitplan, Prompts und Host-Schutz von Transfer v2 mit erfundenen Daten, ohne Modell."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

import aufgaben
import auswerten
import run
from werkzeuge import BASIS, plan_laden, tests, zeitplan

PLAN = plan_laden()
SHA = hashlib.sha256((BASIS / "bedingungen.json").read_bytes()).hexdigest()
EINGESCHLOSSEN = {"A": aufgaben.KANDIDATEN["A"][:4], "B": aufgaben.KANDIDATEN["B"][:4]}


def ergebnis(lauf, ziel="bestanden", uebrige=None, technisch=False):
    von = len(tests(lauf["aufgabe"])["uebrige"])
    return {**lauf, "zielstatus": "nicht_beobachtbar" if technisch else ziel,
            "uebrige_ok": 0 if technisch else (von if uebrige is None else uebrige),
            "uebrige_von": von, "technischer_fehler": "URLError" if technisch else None,
            "abgeschnitten": False, "abbruch": None, "diagnose": {}}


def einstellungen(stufe, eingeschlossen=None):
    return {"stufe": stufe, "commit": "abc", "attrappe": False, "plan_sha256": SHA,
            "eingeschlossen": eingeschlossen}


def vorlauf_daten(regel):
    """regel(lauf) -> (zielstatus, technisch)"""
    daten = []
    for lauf in zeitplan("vorlauf", PLAN):
        ziel, tech = regel(lauf)
        daten.append(ergebnis(lauf, ziel, technisch=tech))
    return daten


def gut_vorlauf(lauf):
    if lauf["aufgabe"] in aufgaben.GEGENFAELLE.values() or lauf["bedingung"] == "D":
        return "bestanden", False
    return "verfehlt", False


def haupt_daten(regel):
    namen = [n for g in ("A", "B") for n in EINGESCHLOSSEN[g]]
    return [ergebnis(l, regel(l)) for l in zeitplan("haupt", PLAN, namen)]


def effekt(lauf):
    """Passend besteht in allen Paaren, unpassend und O nur bei den ersten 4 Seeds."""
    g = aufgaben.gruppe(lauf["aufgabe"])
    return "bestanden" if lauf["bedingung"] == g or lauf["seed"] <= 2104 else "verfehlt"


class Grundlagen(unittest.TestCase):
    def test_mcnemar(self):
        self.assertEqual(auswerten.mcnemar_einseitig(0, 0), 1.0)
        self.assertAlmostEqual(auswerten.mcnemar_einseitig(6, 1), 8 / 128)

    def test_zeitplaene_vollstaendig_und_wiederholbar(self):
        self.assertEqual(len(zeitplan("vorlauf", PLAN)), 12 * 2 * 8 + 2 * 8)
        namen = [n for g in ("A", "B") for n in EINGESCHLOSSEN[g]]
        haupt = zeitplan("haupt", PLAN, namen)
        self.assertEqual(haupt, zeitplan("haupt", PLAN, namen))
        self.assertEqual(len(haupt), 8 * 3 * 15)
        paare = {}
        for l in haupt:
            paare.setdefault((l["aufgabe"], l["seed"]), []).append(l["bedingung"])
        self.assertTrue(all(sorted(b) == ["A", "B", "O"] for b in paare.values()))
        self.assertEqual(len(zeitplan("gegenfall", PLAN)), 2 * 3 * 20)

    def test_seeds_disjunkt(self):
        alle = [s for st in PLAN["stufen"].values() for s in st["seeds"]]
        self.assertEqual(len(alle), len(set(alle)))

    def test_erfahrungen_gleich_lang(self):
        laenge = {k: sum(len(e["problem"]) + len(e["loesung"]) for e in v)
                  for k, v in PLAN["erfahrungen"].items() if v}
        self.assertEqual(laenge["A"], laenge["B"])

    def test_prompts_unterscheiden_sich_nur_wie_vorgesehen(self):
        ohne = lambda d: {k: v for k, v in d.items() if k != "gedaechtnis"}  # noqa: E731
        for name in ("zitate", "budget", "postleitzahlen"):
            t = {b: json.loads(run.prompt(name, b, PLAN)) for b in ("O", "A", "B")}
            self.assertEqual(ohne(t["A"]), ohne(t["O"]))
            self.assertEqual(ohne(t["B"]), ohne(t["O"]))
        # D gibt es nur im Vorlauf auf Kandidaten, nicht auf Gegenfällen.
        for name in ("zitate", "budget"):
            t = {b: json.loads(run.prompt(name, b, PLAN)) for b in ("O", "D")}
            self.assertEqual(t["D"]["gedaechtnis"], [])
            self.assertEqual(t["D"]["geruest"], t["O"]["geruest"])
            self.assertTrue(t["D"]["aufgabe"].startswith(t["O"]["aufgabe"]))


class Vorlauf(unittest.TestCase):
    def test_alle_gates_erfuellt(self):
        v = auswerten.vorlauf(vorlauf_daten(gut_vorlauf), einstellungen("vorlauf"))
        self.assertTrue(v["weiter"], v["gruende"])
        self.assertEqual(v["eingeschlossen"], EINGESCHLOSSEN)

    def test_g2_zaehlt_technische_ausfaelle_als_bestanden(self):
        def regel(l):
            if l["aufgabe"] == "zitate" and l["bedingung"] == "O":
                return ("bestanden", False) if l["seed"] <= 2003 else ("verfehlt", l["seed"] <= 2005)
            return gut_vorlauf(l)
        v = auswerten.vorlauf(vorlauf_daten(regel), einstellungen("vorlauf"))
        self.assertFalse(v["kandidaten"]["zitate"]["G2"], "3 bestanden + 2 technisch > 4")
        self.assertEqual(v["eingeschlossen"]["A"], aufgaben.KANDIDATEN["A"][1:5])

    def test_g1_braucht_sechs_von_acht(self):
        def regel(l):
            if l["aufgabe"] == "budget" and l["bedingung"] == "D":
                return ("bestanden", False) if l["seed"] <= 2005 else ("verfehlt", False)
            return gut_vorlauf(l)
        v = auswerten.vorlauf(vorlauf_daten(regel), einstellungen("vorlauf"))
        self.assertFalse(v["kandidaten"]["budget"]["G1"])
        self.assertNotIn("budget", v["eingeschlossen"]["B"])

    def test_zu_wenige_aufgaben_oder_gegenfall_beenden(self):
        def regel(l):
            if l["aufgabe"] in aufgaben.KANDIDATEN["A"][:4] and l["bedingung"] == "D":
                return "verfehlt", False
            return gut_vorlauf(l)
        v = auswerten.vorlauf(vorlauf_daten(regel), einstellungen("vorlauf"))
        self.assertFalse(v["weiter"])
        self.assertEqual(len(v["eingeschlossen"]["A"]), 2)

        def regel_g4(l):
            if l["aufgabe"] == "gewohnheiten":
                return "verfehlt", False
            return gut_vorlauf(l)
        self.assertFalse(auswerten.vorlauf(vorlauf_daten(regel_g4), einstellungen("vorlauf"))["weiter"])

    def test_unvollstaendig_oder_zu_viele_technische_ausfaelle(self):
        daten = vorlauf_daten(gut_vorlauf)
        self.assertFalse(auswerten.vorlauf(daten[:-1], einstellungen("vorlauf"))["weiter"])
        technisch = vorlauf_daten(lambda l: ("verfehlt", l["nr"] <= 30) if l["nr"] <= 30 else gut_vorlauf(l))
        self.assertFalse(auswerten.vorlauf(technisch, einstellungen("vorlauf"))["gueltig"])


class Haupt(unittest.TestCase):
    def bericht(self, daten):
        return auswerten.haupt(daten, einstellungen("haupt", EINGESCHLOSSEN))

    def test_klarer_effekt(self):
        h = self.bericht(haupt_daten(effekt))
        self.assertTrue(h["gueltig"], h["probleme"])
        self.assertTrue(h["erfolgskriterium"])
        self.assertTrue(h["schadensgrenze_uebrige"])

    def test_nur_unspezifischer_effekt_ist_kein_erfolg(self):
        h = self.bericht(haupt_daten(lambda l: "verfehlt" if l["bedingung"] == "O" or l["seed"] > 2108 else "bestanden"))
        self.assertFalse(h["erfolgskriterium"])
        self.assertGreater(h["nebenauswertung_unpassend_gegen_O_pp"], 0)

    def test_richtung_in_einer_gruppe_falsch(self):
        def regel(l):
            if aufgaben.gruppe(l["aufgabe"]) == "B":
                return "bestanden" if l["bedingung"] == "A" else "verfehlt"
            return effekt(l)
        self.assertFalse(self.bericht(haupt_daten(regel))["erfolgskriterium"])

    def test_zwei_gegenlaeufige_aufgaben(self):
        def regel(l):
            if l["aufgabe"] in EINGESCHLOSSEN["A"][:2]:
                return "bestanden" if l["bedingung"] == "B" else "verfehlt"
            return effekt(l)
        h = self.bericht(haupt_daten(regel))
        self.assertEqual(h["kriterien"]["gegenlaeufige_aufgaben_je_gruppe"]["A"], 2)
        self.assertFalse(h["erfolgskriterium"])

    def test_unvollstaendig_nie_erfolg(self):
        h = self.bericht(haupt_daten(effekt)[:200])
        self.assertFalse(h["gueltig"])
        self.assertFalse(h["erfolgskriterium"])

    def test_schadensgrenze_exakt(self):
        def mit_schaden(fehlend):
            daten = []
            for l in zeitplan("haupt", PLAN, [n for g in ("A", "B") for n in EINGESCHLOSSEN[g]]):
                von = len(tests(l["aufgabe"])["uebrige"])
                g = aufgaben.gruppe(l["aufgabe"])
                daten.append(ergebnis(l, effekt(l), uebrige=von - (1 if l["bedingung"] == g and l["nr"] % 100 < fehlend else 0)))
            return self.bericht(daten)
        self.assertTrue(mit_schaden(0)["schadensgrenze_uebrige"])
        self.assertFalse(mit_schaden(100)["schadensgrenze_uebrige"])


class GegenfallUndGesamt(unittest.TestCase):
    def test_grenze_plus_drei(self):
        def daten(fehl_hinweis):
            out = []
            for l in zeitplan("gegenfall", PLAN):
                hinweis = auswerten.GEGENFALL_HINWEIS[l["aufgabe"]]
                schlecht = l["bedingung"] == hinweis and l["seed"] - 2200 <= fehl_hinweis
                out.append(ergebnis(l, "verfehlt" if schlecht else "bestanden"))
            return auswerten.gegenfall(out, einstellungen("gegenfall"))
        self.assertTrue(daten(3)["schadensgrenze_gegenfaelle"])
        self.assertFalse(daten(4)["schadensgrenze_gegenfaelle"])

    def test_gesamt(self):
        v = {**auswerten.vorlauf(vorlauf_daten(gut_vorlauf), einstellungen("vorlauf")), "commit": "a", "attrappe": False}
        h = {**auswerten.haupt(haupt_daten(effekt), einstellungen("haupt", EINGESCHLOSSEN)), "commit": "a", "attrappe": False}
        g = {**auswerten.gegenfall([ergebnis(l) for l in zeitplan("gegenfall", PLAN)], einstellungen("gegenfall")),
             "commit": "a", "attrappe": False}
        alle = {"vorlauf": v, "haupt": h, "gegenfall": g}
        self.assertTrue(auswerten.gesamt(alle)["bestanden"])
        self.assertFalse(auswerten.gesamt({"vorlauf": v, "haupt": h})["bestanden"])
        self.assertFalse(auswerten.gesamt({**alle, "gegenfall": {**g, "commit": "b"}})["bestanden"])
        self.assertFalse(auswerten.gesamt({**alle, "haupt": {**h, "attrappe": True}})["bestanden"])
        self.assertFalse(auswerten.gesamt({**alle, "vorlauf": {**v, "weiter": False}})["bestanden"])


class Host(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_http_fehler_speichert_anfrage(self):
        class Kaputt(run.Modell):
            @staticmethod
            def senden(nutzlast, lauf):
                raise urllib.error.URLError("verweigert")

        lauf = zeitplan("vorlauf", PLAN)[0]
        e = run.lauf_ausfuehren(lauf, self.tmp / "l", PLAN, Kaputt)
        anfrage = json.loads((self.tmp / "l" / "generierung.json").read_text(encoding="utf-8"))["anfrage"]
        self.assertIn("URLError", e["technischer_fehler"])
        self.assertEqual(e["zielstatus"], "nicht_beobachtbar")
        self.assertEqual(anfrage["options"]["seed"], lauf["seed"])

    def test_vorlauf_freigabe(self):
        with self.assertRaises(SystemExit):
            run.vorlauf_freigabe(None, "abc", False)

    def test_veraendertes_ergebnis_abgewiesen(self):
        befehl = [sys.executable, str(Path(run.__file__)), "--stufe", "vorlauf",
                  "--ausgabe", str(self.tmp / "v"), "--attrappe"]
        self.assertEqual(subprocess.run(befehl, capture_output=True).returncode, 0)
        datei = sorted((self.tmp / "v").glob("*/ergebnis.json"))[0]
        daten = json.loads(datei.read_text(encoding="utf-8"))
        datei.write_text(json.dumps({**daten, "seed": 4242}), encoding="utf-8")
        lauf = subprocess.run(befehl, capture_output=True, text=True)
        self.assertNotEqual(lauf.returncode, 0)
        self.assertIn("passt nicht zum Zeitplan", lauf.stderr)

    def test_haupt_ohne_freigabe_der_attrappe_im_echten_modus(self):
        befehl = [sys.executable, str(Path(run.__file__)), "--stufe", "vorlauf",
                  "--ausgabe", str(self.tmp / "v"), "--attrappe"]
        subprocess.run(befehl, capture_output=True, check=True)
        with self.assertRaises(SystemExit):
            run.vorlauf_freigabe(self.tmp / "v", run.git_stand()[0], False)


if __name__ == "__main__":
    unittest.main(verbosity=1)
