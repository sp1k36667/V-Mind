#!/usr/bin/env python3
"""Wertet alle Durchgänge eines Ausgabeordners der Lernkurve nach Bedingung und Position aus."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

NICHT_BESTANDEN = 6  # höchstens 5 Versuche; nicht bestanden zählt als 6


def kennzahlen(aufgaben):
    erster = [a["versuche"][0] for a in aufgaben]
    bis_bestanden = []
    for a in aufgaben:
        if a["bestanden"]:
            bis_bestanden.append(sum(v["ms"] for v in a["versuche"]))
    return {
        "n": len(aufgaben),
        "erfolg_erster_versuch": mean(a["erster_versuch_bestanden"] for a in aufgaben),
        "anteil_ok_erster_versuch": mean(v["ok"] / v["von"] for v in erster),
        "versuche": mean(len(a["versuche"]) if a["bestanden"] else NICHT_BESTANDEN
                         for a in aufgaben),
        "bestanden": mean(a["bestanden"] for a in aufgaben),
        "modellzeit_bis_bestanden_s": (mean(bis_bestanden) / 1000) if bis_bestanden else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ausgabe", type=Path)
    parser.add_argument("--json", action="store_true")
    opt = parser.parse_args()
    berichte = [json.loads(p.read_text()) for p in sorted(opt.ausgabe.glob("*/ergebnis.json"))]
    nach_position = defaultdict(list)
    lehren = defaultdict(lambda: defaultdict(int))
    for bericht in berichte:
        for aufgabe in bericht["aufgaben"]:
            nach_position[(bericht["bedingung"], aufgabe["position"])].append(aufgabe)
            for lehre in aufgabe["lehren"]:
                zaehler = lehren[bericht["bedingung"]]
                zaehler["vorgeschlagen"] += 1
                zaehler["abgewiesen"] += lehre["abgewiesen"] is not None
                zaehler["validiert"] += bool(lehre.get("validiert"))
    tabelle = {f"{b}/{p}": kennzahlen(a) for (b, p), a in sorted(nach_position.items())}
    if opt.json:
        print(json.dumps({"positionen": tabelle, "lehren": lehren}, ensure_ascii=False, indent=2))
        return
    print(f"{len(berichte)} Durchgänge\n")
    print("Bed./Pos  n  Erfolg 1.V.  OK-Anteil 1.V.  Versuche  bestanden  Modellzeit s")
    for schluessel, k in tabelle.items():
        zeit = "–" if k["modellzeit_bis_bestanden_s"] is None else f"{k['modellzeit_bis_bestanden_s']:.1f}"
        print(f"{schluessel:<9}{k['n']:>2}  {k['erfolg_erster_versuch']:>10.0%}  "
              f"{k['anteil_ok_erster_versuch']:>13.0%}  {k['versuche']:>8.2f}  "
              f"{k['bestanden']:>9.0%}  {zeit:>12}")
    print()
    for bedingung, zaehler in sorted(lehren.items()):
        print(f"Lehren {bedingung}: " + ", ".join(f"{k} {v}" for k, v in zaehler.items()))


if __name__ == "__main__":
    main()
