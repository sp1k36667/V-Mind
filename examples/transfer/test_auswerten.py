#!/usr/bin/env python3
"""Prüft Auswertung, Zeitplan, Host-Schutzregeln und Abnahme-Limits ohne Modell."""

import json
import shutil
import tempfile
import unittest
import urllib.error
from pathlib import Path

import auswerten
import run
import werkzeuge

AUFGABEN_HAUPT = ("ausgaben", "leihliste", "rezepte", "termine")


def ergebnis(lauf, ziel, uebrige=7, technisch=False):
    return {**lauf, "ziel_bestanden": ziel and not technisch, "uebrige_ok": 0 if technisch else uebrige,
            "uebrige_von": 7, "technischer_fehler": "URLError" if technisch else None,
            "abgeschnitten": False, "ziel_format_fehler": False, "abbruch": None}


def stufe(name, besteht, **optionen):
    """Ergebnisse genau nach Zeitplan; besteht(lauf) -> bool."""
    return [ergebnis(l, besteht(l), **optionen) for l in werkzeuge.zeitplan(name, werkzeuge.plan_laden())]


def index(lauf):
    return AUFGABEN_HAUPT.index(lauf["aufgabe"]) * 10 + lauf["seed"] - 1001


def klarer_effekt(lauf):
    return lauf["bedingung"] == "L" or index(lauf) < 16


class McNemar(unittest.TestCase):
    def test_bekannte_werte(self):
        self.assertEqual(auswerten.mcnemar_einseitig(0, 0), 1.0)
        self.assertAlmostEqual(auswerten.mcnemar_einseitig(5, 0), 1 / 32)
        self.assertAlmostEqual(auswerten.mcnemar_einseitig(6, 1), 8 / 128)


class Haupt(unittest.TestCase):
    def test_klarer_effekt_erfuellt_kriterium(self):
        bericht = auswerten.haupt(stufe("haupt", klarer_effekt))
        self.assertTrue(bericht["gueltig"], bericht["probleme"])
        self.assertTrue(bericht["erfolgskriterium"])
        self.assertEqual(bericht["kriterien"]["mcnemar_b_c"], [24, 0])

    def test_zu_kleiner_abstand_verfehlt(self):
        bericht = auswerten.haupt(stufe("haupt", lambda l: index(l) < (28 if l["bedingung"] == "L" else 18)))
        self.assertTrue(bericht["gueltig"])
        self.assertFalse(bericht["erfolgskriterium"])

    def test_nur_acht_paare_sind_nie_erfolg(self):
        teil = [e for e in stufe("haupt", klarer_effekt) if e["seed"] in (1009, 1010)]
        bericht = auswerten.haupt(teil)
        self.assertFalse(bericht["gueltig"])
        self.assertFalse(bericht["erfolgskriterium"])
        self.assertFalse(bericht["schadensgrenze_uebrige"])

    def test_viele_technische_ausfaelle_machen_ungueltig(self):
        ergebnisse = [ergebnis(l, True, technisch=l["bedingung"] != "L")
                      for l in werkzeuge.zeitplan("haupt", werkzeuge.plan_laden())]
        bericht = auswerten.haupt(ergebnisse)
        self.assertFalse(bericht["gueltig"])
        self.assertFalse(bericht["erfolgskriterium"])

    def test_dubletten_und_fremde_laeufe_machen_ungueltig(self):
        ergebnisse = stufe("haupt", klarer_effekt)
        doppelt = ergebnisse + [ergebnisse[0]]
        fremd = ergebnisse[1:] + [{**ergebnisse[0], "seed": 4242}]
        for daten in (doppelt, fremd):
            self.assertFalse(auswerten.haupt(daten)["erfolgskriterium"])

    def test_schaden_an_uebrigen_pruefungen(self):
        ergebnisse = [ergebnis(l, klarer_effekt(l), uebrige=6 if l["bedingung"] == "L" else 7)
                      for l in werkzeuge.zeitplan("haupt", werkzeuge.plan_laden())]
        bericht = auswerten.haupt(ergebnisse)
        self.assertTrue(bericht["erfolgskriterium"])
        self.assertFalse(bericht["schadensgrenze_uebrige"])


class VorlaufUndGesamt(unittest.TestCase):
    def test_grenze_sechzig_prozent(self):
        zwoelf = stufe("vorlauf", lambda l: l["nr"] <= 12)
        dreizehn = stufe("vorlauf", lambda l: l["nr"] <= 13)
        self.assertTrue(auswerten.vorlauf(zwoelf)["weiter"])
        self.assertFalse(auswerten.vorlauf(dreizehn)["weiter"])

    def test_unvollstaendiger_vorlauf_erlaubt_nichts(self):
        self.assertFalse(auswerten.vorlauf(stufe("vorlauf", lambda l: False)[:10])["weiter"])

    def test_gesamt_nur_mit_allen_gueltigen_stufen(self):
        berichte = {
            "vorlauf": {**auswerten.vorlauf(stufe("vorlauf", lambda l: False)), "commit": "a", "attrappe": False},
            "haupt": {**auswerten.haupt(stufe("haupt", klarer_effekt)), "commit": "a", "attrappe": False},
            "gegenfall": {**auswerten.gegenfall(stufe("gegenfall", lambda l: True)), "commit": "a", "attrappe": False},
        }
        self.assertTrue(auswerten.gesamt(berichte)["bestanden"])
        self.assertFalse(auswerten.gesamt({k: berichte[k] for k in ("vorlauf", "haupt")})["bestanden"])
        self.assertFalse(auswerten.gesamt({**berichte, "gegenfall": {**berichte["gegenfall"], "commit": "b"}})["bestanden"])
        self.assertFalse(auswerten.gesamt({**berichte, "haupt": {**berichte["haupt"], "attrappe": True}})["bestanden"])


class Zeitplan(unittest.TestCase):
    def test_vollstaendig_gepaart_und_wiederholbar(self):
        plan = werkzeuge.plan_laden()
        erster = werkzeuge.zeitplan("haupt", plan)
        self.assertEqual(erster, werkzeuge.zeitplan("haupt", plan))
        paare = {}
        for e in erster:
            paare.setdefault((e["aufgabe"], e["seed"]), []).append(e["bedingung"])
        self.assertEqual(len(erster), 120)
        self.assertEqual(len(paare), 40)
        self.assertTrue(all(sorted(b) == ["L", "O", "P"] for b in paare.values()))
        self.assertGreater(len({tuple(b) for b in paare.values()}), 1)

    def test_seeds_der_stufen_ueberschneiden_sich_nicht(self):
        alle = [s for st in werkzeuge.plan_laden()["stufen"].values() for s in st["seeds"]]
        self.assertEqual(len(alle), len(set(alle)))

    def test_erfahrung_und_placebo_gleich_lang(self):
        laenge = {k: sum(len(e["problem"]) + len(e["loesung"]) for e in v)
                  for k, v in werkzeuge.plan_laden()["erfahrungen"].items()}
        self.assertEqual(laenge["L"], laenge["P"])
        self.assertEqual(laenge["O"], 0)

    def test_prompt_unterscheidet_sich_nur_im_gedaechtnis(self):
        plan = werkzeuge.plan_laden()
        texte = {b: json.loads(run.prompt("rezepte", b, plan)) for b in "OLP"}
        for b in "LP":
            self.assertEqual({k: v for k, v in texte[b].items() if k != "gedaechtnis"},
                             {k: v for k, v in texte["O"].items() if k != "gedaechtnis"})


class Host(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_http_fehler_speichert_die_anfrage(self):
        class Kaputt(run.Modell):
            @staticmethod
            def senden(nutzlast, lauf):
                raise urllib.error.URLError("verweigert")

        lauf = werkzeuge.zeitplan("haupt", werkzeuge.plan_laden())[0]
        e = run.lauf_ausfuehren(lauf, self.tmp / "lauf", werkzeuge.plan_laden(), Kaputt)
        gespeichert = json.loads((self.tmp / "lauf" / "generierung.json").read_text(encoding="utf-8"))
        self.assertIn("URLError", e["technischer_fehler"])
        self.assertFalse(e["ziel_bestanden"])
        self.assertEqual(gespeichert["anfrage"]["options"]["seed"], lauf["seed"])

    def test_veraendertes_gespeichertes_ergebnis_wird_abgewiesen(self):
        import subprocess
        import sys
        befehl = [sys.executable, str(Path(run.__file__)), "--stufe", "vorlauf",
                  "--ausgabe", str(self.tmp / "v"), "--attrappe"]
        self.assertEqual(subprocess.run(befehl, capture_output=True).returncode, 0)
        datei = sorted((self.tmp / "v").glob("*/ergebnis.json"))[0]
        daten = json.loads(datei.read_text(encoding="utf-8"))
        datei.write_text(json.dumps({**daten, "seed": 4242}), encoding="utf-8")
        lauf = subprocess.run(befehl, capture_output=True, text=True)
        self.assertNotEqual(lauf.returncode, 0)
        self.assertIn("passt nicht zum Zeitplan", lauf.stderr)

    def test_vorlauf_attrappe_gibt_hauptlauf_nicht_frei(self):
        ordner = self.tmp / "vorlauf"
        ordner.mkdir()
        laeufe = werkzeuge.zeitplan("vorlauf", werkzeuge.plan_laden())
        (ordner / "einstellungen.json").write_text(json.dumps(
            {"stufe": "vorlauf", "commit": "abc", "attrappe": True, "laeufe": laeufe}))
        with self.assertRaises(SystemExit):
            run.vorlauf_freigabe_pruefen(ordner, "abc")
        with self.assertRaises(SystemExit):
            run.vorlauf_freigabe_pruefen(None, "abc")


class AbnahmeLimits(unittest.TestCase):
    def ausfuehren(self, skript, zeitlimit=None):
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp)
            (ordner / "verification").mkdir()
            (ordner / "verification" / "abnahme.py").write_text(skript)
            alt = werkzeuge.ABNAHME_ZEITLIMIT
            werkzeuge.ABNAHME_ZEITLIMIT = zeitlimit or alt
            try:
                return werkzeuge.abnahme_ausfuehren(ordner)
            finally:
                werkzeuge.ABNAHME_ZEITLIMIT = alt

    def test_ausgabelimit_beendet_prozess(self):
        e = self.ausfuehren("import sys\nwhile True:\n    sys.stdout.write('x' * 65536)\n")
        self.assertEqual(e["abbruch"], "ausgabelimit")
        self.assertLessEqual(len(e["ausgabe"].encode()), werkzeuge.MAX_AUSGABE_BYTES + 200)

    def test_zeitlimit_beendet_prozessgruppe(self):
        e = self.ausfuehren("import subprocess, sys, time\n"
                            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                            "time.sleep(60)\n", zeitlimit=1)
        self.assertEqual(e["abbruch"], "zeitlimit")

    def test_formatfehler_wird_getrennt_erkannt(self):
        import selbsttest
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp)
            selbsttest.einrichten("rezepte", ordner)
            app = (ordner / "basis.py").read_text()
            (ordner / "basis.py").write_text(app.replace(
                'schreiben(self.path, {"next_id": self.next_id, "items": self.items})',
                'schreiben(self.path, {"next_id": self.next_id, "items": list(self.items.values())})'))
            ausgabe = werkzeuge.abnahme_ausfuehren(ordner)["ausgabe"]
        self.assertTrue(werkzeuge.format_fehler(ausgabe, "test_ziel_ids_nach_neuladen"))
        ohne = selbsttest.pruefen("rezepte", basis_ersetzung=selbsttest.OHNE_UMWANDLUNG)
        self.assertFalse(werkzeuge.format_fehler(ohne["ausgabe"], "test_ziel_ids_nach_neuladen"))


if __name__ == "__main__":
    shutil.rmtree(Path(__file__).parent / "__pycache__", ignore_errors=True)
    unittest.main(verbosity=1)
