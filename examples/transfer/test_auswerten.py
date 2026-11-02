#!/usr/bin/env python3
"""Prüft Auswertung und Zeitplan mit erfundenen Ergebnissen, ohne Modell."""

import unittest

import auswerten
import run


def lauf(aufgabe, seed, bedingung, ziel, uebrige=7):
    return {"aufgabe": aufgabe, "seed": seed, "bedingung": bedingung, "ziel_bestanden": ziel,
            "uebrige_ok": uebrige, "uebrige_von": 7, "technischer_fehler": None,
            "abgeschnitten": False}


class McNemar(unittest.TestCase):
    def test_bekannte_werte(self):
        self.assertEqual(auswerten.mcnemar_einseitig(0, 0), 1.0)
        self.assertAlmostEqual(auswerten.mcnemar_einseitig(5, 0), 1 / 32)
        self.assertAlmostEqual(auswerten.mcnemar_einseitig(6, 1), 8 / 128)
        self.assertLess(auswerten.mcnemar_einseitig(12, 0), 0.001)


class Haupt(unittest.TestCase):
    def daten(self, l_ok, o_ok, p_ok, l_uebrige=7):
        ergebnisse = []
        for i, aufgabe in enumerate(("ausgaben", "leihliste", "rezepte", "termine")):
            for seed in range(1001, 1011):
                k = i * 10 + seed - 1001
                ergebnisse += [lauf(aufgabe, seed, "L", k < l_ok, l_uebrige),
                               lauf(aufgabe, seed, "O", k < o_ok),
                               lauf(aufgabe, seed, "P", k < p_ok)]
        return ergebnisse

    def test_klarer_effekt_erfuellt_kriterium(self):
        # L besteht in allen 40 Paaren, O und P nur in den ersten 16 (alle bei Aufgabe 1/2).
        ergebnis = auswerten.haupt(self.daten(40, 16, 16))
        self.assertTrue(ergebnis["erfolgskriterium"])
        self.assertEqual(ergebnis["kriterien"]["mcnemar_b_c"], [24, 0])
        self.assertEqual(ergebnis["kriterien"]["aufgaben_L_ueber_O"], 3)

    def test_zu_kleiner_abstand_verfehlt(self):
        self.assertFalse(auswerten.haupt(self.daten(28, 18, 18))["erfolgskriterium"])

    def test_schaden_an_uebrigen_pruefungen(self):
        ergebnis = auswerten.haupt(self.daten(40, 16, 16, l_uebrige=6))
        self.assertTrue(ergebnis["erfolgskriterium"])
        self.assertFalse(ergebnis["schadensgrenze_uebrige"])


class Vorlauf(unittest.TestCase):
    def test_grenze_sechzig_prozent(self):
        zwoelf = [lauf("rezepte", s, "O", s < 12) for s in range(20)]
        dreizehn = [lauf("rezepte", s, "O", s < 13) for s in range(20)]
        self.assertTrue(auswerten.vorlauf(zwoelf)["weiter"])
        self.assertFalse(auswerten.vorlauf(dreizehn)["weiter"])

    def test_zu_viele_technische_ausfaelle(self):
        laeufe = [lauf("rezepte", s, "O", False) for s in range(20)]
        for e in laeufe[:3]:
            e["technischer_fehler"] = "URLError"
        self.assertFalse(auswerten.vorlauf(laeufe)["weiter"])


class Zeitplan(unittest.TestCase):
    def test_vollstaendig_gepaart_und_wiederholbar(self):
        plan = run.plan_laden()
        erster = run.zeitplan("haupt", plan)
        self.assertEqual(erster, run.zeitplan("haupt", plan))
        self.assertEqual(len(erster), 120)
        paare = {}
        for e in erster:
            paare.setdefault((e["aufgabe"], e["seed"]), []).append(e["bedingung"])
        self.assertEqual(len(paare), 40)
        self.assertTrue(all(sorted(b) == ["L", "O", "P"] for b in paare.values()))
        self.assertGreater(len({tuple(b) for b in paare.values()}), 1, "Reihenfolge nicht zufällig")

    def test_seeds_der_stufen_ueberschneiden_sich_nicht(self):
        stufen = run.plan_laden()["stufen"]
        alle = [s for st in stufen.values() for s in st["seeds"]]
        self.assertEqual(len(alle), len(set(alle)))

    def test_erfahrung_und_placebo_gleich_lang(self):
        erfahrungen = run.plan_laden()["erfahrungen"]
        laenge = {k: sum(len(e["problem"]) + len(e["loesung"]) for e in v)
                  for k, v in erfahrungen.items()}
        self.assertEqual(laenge["L"], laenge["P"])
        self.assertEqual(laenge["O"], 0)

    def test_prompt_unterscheidet_sich_nur_im_gedaechtnis(self):
        plan = run.plan_laden()
        import json
        texte = {b: json.loads(run.prompt("rezepte", b, plan)) for b in "OLP"}
        for b in "LP":
            self.assertEqual({k: v for k, v in texte[b].items() if k != "gedaechtnis"},
                             {k: v for k, v in texte["O"].items() if k != "gedaechtnis"})


if __name__ == "__main__":
    unittest.main(verbosity=1)
