#!/usr/bin/env python3
"""Auswertung des Transfer-Pilots nach den vorab festgelegten Kriterien.

Aufruf: auswerten.py ORDNER [ORDNER ...]; jeder Ordner enthält eine Stufe von run.py.
Technische Fehler und abgeschnittene Antworten zählen als nicht bestanden und werden
getrennt ausgewiesen."""

import json
import sys
from collections import defaultdict
from math import comb
from pathlib import Path

VORLAUF_HOECHSTENS = 0.60
TECHNISCH_HOECHSTENS = 0.10
MIN_L_UEBER_O_PP = 30
MIN_L_UEBER_P_PP = 20
MIN_AUFGABEN_L_UEBER_O = 3
ALPHA = 0.05
MAX_SCHADEN_PP = 10
MAX_GEGENFALL_MEHR = 1


def mcnemar_einseitig(b, c):
    """Exakter einseitiger McNemar-Test: P(X >= b) bei X ~ Bin(b + c, 1/2).
    b = Paare mit L bestanden und O nicht, c = umgekehrt."""
    n = b + c
    if n == 0:
        return 1.0
    return sum(comb(n, k) for k in range(b, n + 1)) / 2 ** n


def laden(ordner):
    einstellungen = json.loads((ordner / "einstellungen.json").read_text(encoding="utf-8"))
    ergebnisse = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(ordner.glob("*/ergebnis.json"))]
    return einstellungen, ergebnisse


def anteil(werte):
    return sum(werte) / len(werte) if werte else 0.0


def kennzahlen(ergebnisse):
    je_bedingung = defaultdict(list)
    for e in ergebnisse:
        je_bedingung[e["bedingung"]].append(e)
    zusammenfassung = {}
    for bedingung, laeufe in sorted(je_bedingung.items()):
        zusammenfassung[bedingung] = {
            "laeufe": len(laeufe),
            "ziel": sum(e["ziel_bestanden"] for e in laeufe),
            "ziel_anteil": round(anteil([e["ziel_bestanden"] for e in laeufe]), 3),
            "uebrige_anteil": round(sum(e["uebrige_ok"] for e in laeufe)
                                    / max(1, sum(e["uebrige_von"] for e in laeufe)), 3),
            "technisch": sum(bool(e["technischer_fehler"]) for e in laeufe),
            "abgeschnitten": sum(e["abgeschnitten"] for e in laeufe),
        }
    return zusammenfassung


def vorlauf(ergebnisse):
    werte = kennzahlen(ergebnisse)["O"]
    technisch = werte["technisch"] + werte["abgeschnitten"]
    return {"kennzahlen": werte,
            "weiter": werte["ziel_anteil"] <= VORLAUF_HOECHSTENS
            and technisch <= TECHNISCH_HOECHSTENS * werte["laeufe"],
            "regel": f"Ziel höchstens {VORLAUF_HOECHSTENS:.0%} und technische Ausfälle höchstens "
                     f"{TECHNISCH_HOECHSTENS:.0%}"}


def haupt(ergebnisse):
    paare = defaultdict(dict)
    for e in ergebnisse:
        paare[(e["aufgabe"], e["seed"])][e["bedingung"]] = e["ziel_bestanden"]
    vollstaendig = {k: v for k, v in paare.items() if set(v) == {"O", "L", "P"}}
    b = sum(v["L"] and not v["O"] for v in vollstaendig.values())
    c = sum(v["O"] and not v["L"] for v in vollstaendig.values())
    werte = kennzahlen(ergebnisse)
    pp = {k: 100 * werte[k]["ziel_anteil"] for k in ("O", "L", "P")}
    je_aufgabe = defaultdict(lambda: {"O": 0, "L": 0, "P": 0})
    for (aufgabe, _), v in vollstaendig.items():
        for bedingung, ok in v.items():
            je_aufgabe[aufgabe][bedingung] += ok
    aufgaben_l_ueber_o = sum(v["L"] > v["O"] for v in je_aufgabe.values())
    p_wert = mcnemar_einseitig(b, c)
    schaden_pp = 100 * (werte["O"]["uebrige_anteil"] - werte["L"]["uebrige_anteil"])
    kriterien = {
        "L_ueber_O_pp": round(pp["L"] - pp["O"], 1),
        "mcnemar_b_c": [b, c], "mcnemar_p": round(p_wert, 4),
        "L_ueber_P_pp": round(pp["L"] - pp["P"], 1),
        "aufgaben_L_ueber_O": aufgaben_l_ueber_o,
        "schaden_uebrige_pp": round(schaden_pp, 1),
    }
    erfolg = (kriterien["L_ueber_O_pp"] >= MIN_L_UEBER_O_PP and p_wert < ALPHA
              and kriterien["L_ueber_P_pp"] >= MIN_L_UEBER_P_PP
              and aufgaben_l_ueber_o >= MIN_AUFGABEN_L_UEBER_O)
    return {"kennzahlen": werte, "je_aufgabe": dict(je_aufgabe),
            "paare_vollstaendig": len(vollstaendig), "kriterien": kriterien,
            "erfolgskriterium": erfolg, "schadensgrenze_uebrige": schaden_pp <= MAX_SCHADEN_PP}


def gegenfall(ergebnisse):
    werte = kennzahlen(ergebnisse)
    fehl = {k: werte[k]["laeufe"] - werte[k]["ziel"] for k in werte}
    return {"kennzahlen": werte, "fehlanwendungen": fehl,
            "schadensgrenze_gegenfall": fehl.get("L", 0) - fehl.get("O", 0) <= MAX_GEGENFALL_MEHR,
            "hinweis": "Bei 10 Läufen nur beschreibend, kein Nachweis der Unschädlichkeit; "
                       "Ursache jedes Fehlschlags im Rohcode prüfen."}


def main(argv):
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    bericht = {}
    for ordner in map(Path, argv[1:]):
        einstellungen, ergebnisse = laden(ordner)
        stufe = einstellungen["stufe"]
        auswertung = {"vorlauf": vorlauf, "haupt": haupt, "gegenfall": gegenfall}[stufe](ergebnisse)
        auswertung.update(commit=einstellungen["commit"], attrappe=einstellungen["attrappe"],
                          geplant=len(einstellungen["laeufe"]), vorhanden=len(ergebnisse))
        bericht[stufe] = auswertung
    print(json.dumps(bericht, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
