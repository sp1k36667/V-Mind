#!/usr/bin/env python3
"""Regeln, Fallauswahl, Abruf, Arme, Prompt, Host-Schutz und Auswertung von R1 ohne Modell."""

import json
import tempfile
import unittest
from pathlib import Path

import r1_auswerten
import r1_host
import r1_werkzeuge as w

PLAN = w.plan_laden()
AUSWAHL = w.faelle_bestimmen(PLAN)
FAELLE = AUSWAHL["faelle"]


class Fallauswahl(unittest.TestCase):
    def test_reproduzierbar_und_vollstaendig(self):
        self.assertEqual(w.faelle_bestimmen(PLAN), AUSWAHL)
        self.assertEqual(len(AUSWAHL["alle"]), 38)
        self.assertEqual(len(FAELLE), 36)
        self.assertEqual(len(AUSWAHL["gestrichen"]), 2)
        self.assertEqual([f["fall"] for f in FAELLE], list(range(36)))
        self.assertEqual(len({f["seed"] for f in FAELLE}), 36)

    def test_nur_bedingung_o_und_bewertungsaufgaben(self):
        for f in FAELLE:
            ergebnis = json.loads((w.REPO / f["ordner"] / "ergebnis.json").read_text(encoding="utf-8"))
            self.assertEqual(ergebnis["bedingung"], "O")
            self.assertIn(f["aufgabe"], PLAN["bewertungsaufgaben"])
            self.assertTrue(f["nicht_ok"])

    def test_lern_und_bewertungsfaelle_getrennt(self):
        lern = {f["ordner"] for f in w.kandidaten(PLAN, PLAN["lernaufgaben"])}
        self.assertFalse(lern & {f["ordner"] for f in FAELLE})
        self.assertEqual(len(lern), 29)


class Relevanz(unittest.TestCase):
    def eintrag(self, problem, kind="error_solution", status="validated"):
        return {"problem": problem, "kind": kind, "status": status}

    def test_typ_und_bezeichner(self):
        text = "AttributeError: 'Notes' object has no attribute 'list'\n"
        self.assertTrue(w.passend(self.eintrag("AttributeError: object has no attribute 'list'."), text))
        self.assertFalse(w.passend(self.eintrag("AttributeError bei listen von Dingen"), text), "Teilwort zählt nicht")
        self.assertFalse(w.passend(self.eintrag("Methode list() fehlt"), text), "ohne Ausnahmetyp")

    def test_assertion_exakt(self):
        text = "AssertionError: False is not true : IDs nach Neuladen keine int\n"
        self.assertTrue(w.passend(self.eintrag("AssertionError: IDs nach Neuladen keine int. Mehr Text."), text))
        self.assertFalse(w.passend(self.eintrag("IDs nach dem Laden keine Zahl"), text))

    def test_nur_validierte_error_solution(self):
        text = "AttributeError: 'X' object has no attribute 'list'\n"
        problem = "AttributeError: object has no attribute 'list'"
        self.assertFalse(w.passend(self.eintrag(problem, kind="long_term"), text))
        self.assertFalse(w.passend(self.eintrag(problem, status="pending"), text))


class Arme(unittest.TestCase):
    def test_p_gleich_viele_fachfremde_ohne_wiederholung(self):
        texte = w.prompttexte()
        self.assertEqual(w.p_zuteilen([], PLAN, texte), [])
        p = w.p_zuteilen([1, 2], PLAN, texte)
        self.assertEqual(len(p), 2)
        self.assertEqual(len(set(p)), 2)
        self.assertTrue(all(texte[i]["rolle"] == "fachfremd" for i in p))
        self.assertEqual(p, w.p_zuteilen([1, 2], PLAN, texte))

    def test_hinweise_aus_prompttexten_mit_laengengrenze(self):
        texte = w.prompttexte()
        roh = {e["id"]: e for e in json.loads((w.BASIS / "wissen" / "eintraege.json").read_text(encoding="utf-8"))}
        for i in texte:
            h = w.hinweis(i, PLAN, texte)
            self.assertLessEqual(len(h["wann"]), PLAN["prompt"]["wann_max"])
            self.assertLessEqual(len(h["richtig"]), PLAN["prompt"]["richtig_max"])
            self.assertEqual(set(h), {"wann", "richtig"})
        for falsch in ("path < best_path", "if not one_way else []", "if char == '*': and"):
            self.assertFalse(any(falsch in json.dumps(w.hinweis(i, PLAN, texte)) for i in texte), falsch)
            self.assertTrue(any(falsch in e["problem"] for e in roh.values()), "Rohtext enthält das Muster")

    def test_prompt_gleich_bis_auf_gedaechtnis(self):
        fall = FAELLE[0]
        o = json.loads(w.prompt(fall, [], PLAN))
        l = json.loads(w.prompt(fall, [w.hinweis(1, PLAN)], PLAN))
        self.assertEqual({k: v for k, v in o.items() if k != "gedaechtnis"},
                         {k: v for k, v in l.items() if k != "gedaechtnis"})
        self.assertLessEqual(len(o["pruefausgabe"]), PLAN["prompt"]["pruefausgabe_max"])
        self.assertIn("app.py", o["zieldatei"])


class Zeitplan(unittest.TestCase):
    def test_108_gepaart_und_wiederholbar(self):
        plan = w.zeitplan(FAELLE, PLAN)
        self.assertEqual(plan, w.zeitplan(FAELLE, PLAN))
        self.assertEqual(len(plan), 108)
        je_fall = {}
        for lauf in plan:
            je_fall.setdefault(lauf["fall"], []).append(lauf["arm"])
            self.assertEqual(lauf["seed"], FAELLE[lauf["fall"]]["seed"])
        self.assertTrue(all(sorted(a) == ["L", "O", "P"] for a in je_fall.values()))


class Host(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.wurzel = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_grenze_und_keine_wiederholung(self):
        lauf = {"nr": 1, "fall": 0, "arm": "O", "aufgabe": "rezepte", "seed": 7000}
        r1_host.aufruf_anmelden(self.wurzel, lauf, PLAN)
        with self.assertRaises(SystemExit):
            r1_host.aufruf_anmelden(self.wurzel, lauf, PLAN)
        with (self.wurzel / r1_host.PROTOKOLL).open("a", encoding="utf-8") as datei:
            for nr in range(2, PLAN["max_aufrufe"] + 1):
                datei.write(json.dumps({"nr": nr}) + "\n")
        with self.assertRaises(SystemExit):
            r1_host.aufruf_anmelden(self.wurzel, {**lauf, "nr": 999}, PLAN)

    def test_abweichende_vorbereitung_stoppt(self):
        r1_host.sichern(self.wurzel / "x.json", {"a": 1})
        r1_host.sichern(self.wurzel / "x.json", {"a": 1})
        with self.assertRaises(SystemExit):
            r1_host.sichern(self.wurzel / "x.json", {"a": 2})


def ergebnis(lauf, repariert, regression=(), technisch=False, unbekannt=False):
    return {**lauf, "repariert": repariert and not technisch, "regression": None if unbekannt else list(regression),
            "technischer_fehler": "URLError" if technisch else None, "dauer_s": 30.0, "ausgabe_tokens": 1000}


class Auswertung(unittest.TestCase):
    def daten(self, regel):
        laeufe = w.zeitplan(FAELLE, PLAN)
        abruf = {str(f["fall"]): {"l_ids": [1] if f["fall"] < 30 else [], "klasse": "richtig" if f["fall"] < 30 else "leer"}
                 for f in FAELLE}
        return {"laeufe": laeufe, "attrappe": False, "commit": "abc"}, AUSWAHL, abruf, [ergebnis(l, **regel(l)) for l in laeufe]

    def test_effekt_erfuellt_kriterien(self):
        b = r1_auswerten.auswerten(*self.daten(lambda l: {"repariert": l["arm"] == "L" and l["fall"] < 20 or l["fall"] < 5}), PLAN)
        self.assertTrue(b["gueltig"])
        self.assertTrue(b["pilot_ueber_schwellen"], b["kriterien"])

    def test_kein_effekt_verfehlt(self):
        b = r1_auswerten.auswerten(*self.daten(lambda l: {"repariert": l["fall"] < 10}), PLAN)
        self.assertFalse(b["pilot_ueber_schwellen"])

    def test_nur_unspezifisch_verfehlt_l_minus_p(self):
        b = r1_auswerten.auswerten(*self.daten(lambda l: {"repariert": l["arm"] != "O" and l["fall"] < 20 or l["fall"] < 5}), PLAN)
        self.assertFalse(b["kriterien"]["l_minus_p"]["erfuellt"])

    def test_regression_und_sensitivitaet(self):
        b = r1_auswerten.auswerten(*self.daten(lambda l: {"repariert": l["arm"] == "L" and l["fall"] < 20 or l["fall"] < 5,
                                                          "unbekannt": l["arm"] == "L" and 20 <= l["fall"] < 25}), PLAN)
        self.assertEqual(b["kennzahlen"]["L"]["regression_unbekannt"], 5)
        self.assertFalse(b["kriterien"]["regression"]["erfuellt"], "Sensitivität: 5/36 > 10 pp")

    def test_technische_ausfaelle_machen_ungueltig(self):
        b = r1_auswerten.auswerten(*self.daten(lambda l: {"repariert": False, "technisch": l["nr"] <= 11}), PLAN)
        self.assertFalse(b["gueltig"])
        b = r1_auswerten.auswerten(*self.daten(lambda l: {"repariert": False, "technisch": l["nr"] <= 10}), PLAN)
        self.assertTrue(b["gueltig"])

    def test_fehlender_lauf_macht_ungueltig(self):
        e, a, ab, r = self.daten(lambda l: {"repariert": False})
        self.assertFalse(r1_auswerten.auswerten(e, a, ab, r[1:], PLAN)["gueltig"])

    def test_mcnemar(self):
        self.assertEqual(r1_auswerten.mcnemar_einseitig(0, 0), 1.0)
        self.assertAlmostEqual(r1_auswerten.mcnemar_einseitig(6, 1), 8 / 128)


if __name__ == "__main__":
    unittest.main(verbosity=1)
