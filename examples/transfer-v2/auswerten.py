#!/usr/bin/env python3
"""Auswertung von Transfer v2 nach den vorab festgelegten Regeln des Plans.

Aufruf: auswerten.py VORLAUF [HAUPT [GEGENFALL]] (je ein Ordner von run.py). Eine Stufe ist
nur gültig, wenn ihre Läufe genau dem Zeitplan entsprechen, bedingungen.json unverändert
ist und höchstens 10 % der geplanten Läufe technisch ausfielen. Ungültig heißt nie
bestanden. Alle Grenzen werden exakt (Bruchzahlen) vor jeder Rundung geprüft."""

import hashlib
import json
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from math import comb
from pathlib import Path

import aufgaben
from werkzeuge import BASIS, plan_laden, tests, zeitplan

IDENTITAET = ("nr", "aufgabe", "bedingung", "seed")
PASSEND = {"A": "A", "B": "B"}
UNPASSEND = {"A": "B", "B": "A"}
GEGENFALL_HINWEIS = {"postleitzahlen": "A", "gewohnheiten": "B"}


def mcnemar_einseitig(b, c):
    """P(X >= b) bei X ~ Bin(b + c, 1/2); exakt nur bei austauschbaren Paaren."""
    n = b + c
    return 1.0 if n == 0 else sum(comb(n, k) for k in range(b, n + 1)) / 2 ** n


def technisch(e):
    return bool(e["technischer_fehler"]) or bool(e["abgeschnitten"])


def gueltigkeit(stufe, ergebnisse, einstellungen):
    plan = plan_laden()
    probleme = []
    if einstellungen.get("plan_sha256") != hashlib.sha256((BASIS / "bedingungen.json").read_bytes()).hexdigest():
        probleme.append("bedingungen.json seit dem Lauf verändert")
    eingeschlossen = einstellungen.get("eingeschlossen")
    namen = [n for g in ("A", "B") for n in eingeschlossen[g]] if eingeschlossen else None
    erwartet = [tuple(l[k] for k in IDENTITAET) for l in zeitplan(stufe, plan, namen)]
    vorhanden = [tuple(e.get(k) for k in IDENTITAET) for e in ergebnisse]
    zaehler = Counter(vorhanden)
    if any(n > 1 for n in zaehler.values()):
        probleme.append("doppelte Läufe")
    if set(vorhanden) - set(erwartet):
        probleme.append("Läufe nicht im Zeitplan")
    fehlend = set(erwartet) - set(vorhanden)
    if fehlend:
        probleme.append(f"{len(fehlend)} von {len(erwartet)} geplanten Läufen fehlen")
    ausfaelle = sum(technisch(e) for e in ergebnisse)
    if Fraction(ausfaelle, max(len(erwartet), 1)) > Fraction(str(plan["gates"]["technisch_hoechstens"])):
        probleme.append(f"{ausfaelle} technische Ausfälle (über 10 %)")
    return probleme


def zaehlen(laeufe):
    return {
        "laeufe": len(laeufe),
        "bestanden": sum(e["zielstatus"] == "bestanden" for e in laeufe),
        "verfehlt": sum(e["zielstatus"] == "verfehlt" for e in laeufe),
        "nicht_beobachtbar": sum(e["zielstatus"] == "nicht_beobachtbar" for e in laeufe),
        "technisch": sum(technisch(e) for e in laeufe),
        "uebrige_ok": sum(e["uebrige_ok"] for e in laeufe),
        "uebrige_von": sum(e["uebrige_von"] for e in laeufe),
    }


def vorlauf(ergebnisse, einstellungen):
    plan = plan_laden()
    gates = plan["gates"]
    probleme = gueltigkeit("vorlauf", ergebnisse, einstellungen)
    je = defaultdict(list)
    for e in ergebnisse:
        je[(e["aufgabe"], e["bedingung"])].append(e)
    kandidaten = {}
    for g in ("A", "B"):
        for name in aufgaben.KANDIDATEN[g]:
            o, d = zaehlen(je[(name, "O")]), zaehlen(je[(name, "D")])
            g1 = d["bestanden"] >= gates["g1_min"]
            # Konservativ: Ein technischer Ausfall unter O zählt für G2 wie ein Bestehen.
            g2 = o["bestanden"] + o["technisch"] <= gates["g2_max"]
            # G3 über die technisch gültigen O-Läufe; fehlende Läufe machen die Stufe ungültig,
            # technische Ausfälle sind je Stufe auf 10 % begrenzt.
            gueltige = o["laeufe"] - o["technisch"]
            g3 = gueltige > 0 and (Fraction(o["uebrige_ok"], gueltige * len(tests(name)["uebrige"]))
                                   >= Fraction(str(gates["g3_min_anteil"])))
            kandidaten[name] = {"gruppe": g, "O": o, "D": d, "G1": g1, "G2": g2, "G3": g3,
                                "erfuellt": g1 and g2 and g3}
    eingeschlossen = {g: [n_ for n_ in aufgaben.KANDIDATEN[g] if kandidaten[n_]["erfuellt"]][:gates["je_gruppe"]]
                      for g in ("A", "B")}
    gegenfaelle = {}
    for name in aufgaben.GEGENFAELLE.values():
        o = zaehlen(je[(name, "O")])
        gegenfaelle[name] = {"O": o, "G4": o["bestanden"] >= gates["g4_min"]}
    gruende = list(probleme)
    for g in ("A", "B"):
        if len(eingeschlossen[g]) < gates["min_je_gruppe"]:
            gruende.append(f"Gruppe {g} nicht auswertbar ({len(eingeschlossen[g])} Aufgaben)")
    for name, w in gegenfaelle.items():
        if not w["G4"]:
            gruende.append(f"Gegenfall {name} nicht prüfbar (G4)")
    return {"gueltig": not probleme, "probleme": probleme, "kandidaten": kandidaten,
            "eingeschlossen": eingeschlossen, "gegenfaelle": gegenfaelle,
            "weiter": not gruende, "gruende": gruende}


def haupt(ergebnisse, einstellungen):
    plan = plan_laden()
    k = plan["kriterien"]
    probleme = gueltigkeit("haupt", ergebnisse, einstellungen)
    eingeschlossen = einstellungen["eingeschlossen"]
    gruppe_von = {n: g for g in ("A", "B") for n in eingeschlossen[g]}
    paare = defaultdict(dict)
    for e in ergebnisse:
        paare[(e["aufgabe"], e["seed"])][e["bedingung"]] = e
    b = c = 0
    je_aufgabe = defaultdict(lambda: {"passend": 0, "unpassend": 0, "O": 0})
    passend_laeufe, unpassend_laeufe, o_laeufe = [], [], []
    for (name, _), v in paare.items():
        g = gruppe_von.get(name)
        if g is None or not {"O", "A", "B"} <= set(v):
            continue
        p, u, o = v[PASSEND[g]], v[UNPASSEND[g]], v["O"]
        pb, ub = p["zielstatus"] == "bestanden", u["zielstatus"] == "bestanden"
        b += pb and not ub
        c += ub and not pb
        je_aufgabe[name]["passend"] += pb
        je_aufgabe[name]["unpassend"] += ub
        je_aufgabe[name]["O"] += o["zielstatus"] == "bestanden"
        passend_laeufe.append(p)
        unpassend_laeufe.append(u)
        o_laeufe.append(o)
    zp, zu, zo = zaehlen(passend_laeufe), zaehlen(unpassend_laeufe), zaehlen(o_laeufe)
    abstand = (100 * Fraction(zp["bestanden"] - zu["bestanden"], zp["laeufe"])
               if zp["laeufe"] else Fraction(0))
    p_wert = mcnemar_einseitig(b, c)
    richtung = {g: sum(je_aufgabe[n]["passend"] for n in eingeschlossen[g])
                > sum(je_aufgabe[n]["unpassend"] for n in eingeschlossen[g]) for g in ("A", "B")}
    gegen = {g: sum(je_aufgabe[n]["passend"] < je_aufgabe[n]["unpassend"] for n in eingeschlossen[g])
             for g in ("A", "B")}
    schaden = (100 * (Fraction(zo["uebrige_ok"], zo["uebrige_von"]) - Fraction(zp["uebrige_ok"], zp["uebrige_von"]))
               if zo["uebrige_von"] and zp["uebrige_von"] else Fraction(0))
    erfolg = (not probleme and abstand >= k["min_abstand_pp"] and p_wert < k["alpha"]
              and all(richtung.values()) and all(n <= 1 for n in gegen.values()))
    diagnose = {b_: Counter(e["diagnose"].get("test_diag_false_abgelehnt") for e in ergebnisse
                            if e["bedingung"] == b_ and gruppe_von.get(e["aufgabe"]) == "B")
                for b_ in ("O", "A", "B")}
    return {"gueltig": not probleme, "probleme": probleme, "passend": zp, "unpassend": zu, "O": zo,
            "je_aufgabe": dict(je_aufgabe),
            "kriterien": {"abstand_pp": round(float(abstand), 1), "mcnemar_b_c": [b, c],
                          "mcnemar_p": round(p_wert, 4), "richtung_je_gruppe": richtung,
                          "gegenlaeufige_aufgaben_je_gruppe": gegen,
                          "schaden_uebrige_pp": round(float(schaden), 1)},
            "erfolgskriterium": erfolg,
            "schadensgrenze_uebrige": not probleme and schaden <= k["max_schaden_pp"],
            "nebenauswertung_unpassend_gegen_O_pp": round(float(
                100 * Fraction(zu["bestanden"] - zo["bestanden"], zo["laeufe"])), 1) if zo["laeufe"] else None,
            "diagnose_false_gruppe_b": {k_: dict(v) for k_, v in diagnose.items()}}


def gegenfall(ergebnisse, einstellungen):
    k = plan_laden()["kriterien"]
    probleme = gueltigkeit("gegenfall", ergebnisse, einstellungen)
    je = defaultdict(list)
    for e in ergebnisse:
        je[(e["aufgabe"], e["bedingung"])].append(e)
    faelle = {}
    for name, hinweis in GEGENFALL_HINWEIS.items():
        werte = {b_: zaehlen(je[(name, b_)]) for b_ in ("O", "A", "B")}
        fehl = {b_: w["laeufe"] - w["bestanden"] for b_, w in werte.items()}
        faelle[name] = {"hinweis": hinweis, "werte": werte, "fehlschlaege": fehl,
                        "grenze_eingehalten": fehl[hinweis] - fehl["O"] <= k["gegenfall_grenze"]}
    return {"gueltig": not probleme, "probleme": probleme, "faelle": faelle,
            "schadensgrenze_gegenfaelle": not probleme and all(f["grenze_eingehalten"] for f in faelle.values())}


STUFEN = {"vorlauf": vorlauf, "haupt": haupt, "gegenfall": gegenfall}


def stufe_auswerten(ordner):
    ordner = Path(ordner)
    einstellungen = json.loads((ordner / "einstellungen.json").read_text(encoding="utf-8"))
    ergebnisse = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(ordner.glob("*/ergebnis.json"))]
    bericht = STUFEN[einstellungen["stufe"]](ergebnisse, einstellungen)
    bericht.update(stufe=einstellungen["stufe"], commit=einstellungen["commit"],
                   attrappe=einstellungen["attrappe"])
    return bericht


def gesamt(berichte):
    """Gesamterfolg nur mit allen drei gültigen Stufen am selben Commit, ohne Attrappe."""
    if set(berichte) != set(STUFEN):
        return {"bestanden": False, "gruende": ["nicht alle Stufen ausgewertet"]}
    v, h, g = berichte["vorlauf"], berichte["haupt"], berichte["gegenfall"]
    gruende = []
    if len({b["commit"] for b in berichte.values()}) != 1:
        gruende.append("Stufen von verschiedenen Commits")
    if any(b["attrappe"] for b in berichte.values()):
        gruende.append("Attrappe, keine Messdaten")
    if not v["weiter"]:
        gruende.append("Vorlauf erlaubt keine Fortsetzung")
    if not h["gueltig"]:
        gruende.append("Hauptlauf ungültig")
    elif not h["erfolgskriterium"]:
        gruende.append("Erfolgskriterium verfehlt")
    elif not h["schadensgrenze_uebrige"]:
        gruende.append("Schadensgrenze übrige Prüfungen verletzt")
    if not g["gueltig"]:
        gruende.append("Gegenfälle ungültig")
    elif not g["schadensgrenze_gegenfaelle"]:
        gruende.append("Schadensgrenze Gegenfall verletzt")
    return {"bestanden": not gruende, "gruende": gruende}


def main(argv):
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    berichte = {}
    for ordner in argv[1:]:
        bericht = stufe_auswerten(ordner)
        if bericht["stufe"] in berichte:
            print(f"Stufe {bericht['stufe']} doppelt angegeben", file=sys.stderr)
            return 2
        berichte[bericht["stufe"]] = bericht
    berichte["gesamt"] = gesamt(berichte)
    print(json.dumps(berichte, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
