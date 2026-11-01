#!/usr/bin/env python3
"""Wertet alle Durchgänge eines Ausgabeordners der Lernkurve nach Bedingung und Position aus."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

NICHT_BESTANDEN = 6  # höchstens 5 Versuche; nicht bestanden zählt als 6
SPAETE_POSITIONEN = (4, 5, 6)  # Erfolgskriterium laut Plan


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
        "mit_gedaechtnis": mean(bool(a["gedaechtnis_ids"]) for a in aufgaben),
    }


def spaet(bericht, wert):
    return mean(wert(a) for a in bericht["aufgaben"] if a["position"] in SPAETE_POSITIONEN)


def paarvergleich(berichte):
    """Je Reihenfolge und Seed: Bedingung minus A auf den späten Positionen."""
    paare = defaultdict(dict)
    for b in berichte:
        paare[(b["folge_nr"], b["seed"])][b["bedingung"]] = b
    zeilen = []
    for (folge, seed), je in sorted(paare.items()):
        if "A" not in je:
            continue
        a = je["A"]
        zeile = {"folge": folge, "seed": seed}
        for bed in ("B", "C"):
            if bed not in je:
                continue
            for name, wert in (("erfolg", lambda x: x["erster_versuch_bestanden"]),
                               ("ok_anteil", lambda x: x["versuche"][0]["ok"] / x["versuche"][0]["von"])):
                zeile[f"{bed}-A_{name}"] = spaet(je[bed], wert) - spaet(a, wert)
        zeilen.append(zeile)
    return zeilen


def lehren_liste(berichte):
    liste = []
    for b in berichte:
        for a in b["aufgaben"]:
            for lehre in a["lehren"]:
                liste.append({"bedingung": b["bedingung"], "durchgang": f"r{b['folge_nr']}-s{b['seed']}",
                              "aufgabe": a["aufgabe"], "test": lehre["test"],
                              "validiert": lehre.get("validiert"), "abgewiesen": lehre["abgewiesen"],
                              "diff": lehre.get("diff_zeichen", 0) > 0, **(lehre["lehre"] or {})})
    return liste


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ausgabe", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--lehren", action="store_true", help="alle Lehren einzeln ausgeben")
    opt = parser.parse_args()
    berichte = [json.loads(p.read_text()) for p in sorted(opt.ausgabe.glob("*/ergebnis.json"))]
    nach_position = defaultdict(list)
    zaehler = defaultdict(lambda: defaultdict(int))
    for bericht in berichte:
        for aufgabe in bericht["aufgaben"]:
            nach_position[(bericht["bedingung"], aufgabe["position"])].append(aufgabe)
            for lehre in aufgabe["lehren"]:
                z = zaehler[bericht["bedingung"]]
                z["vorgeschlagen"] += 1
                z["abgewiesen"] += lehre["abgewiesen"] is not None
                z["validiert"] += bool(lehre.get("validiert"))
    tabelle = {f"{b}/{p}": kennzahlen(a) for (b, p), a in sorted(nach_position.items())}
    paare = paarvergleich(berichte)
    if opt.lehren:
        for lehre in lehren_liste(berichte):
            print(json.dumps(lehre, ensure_ascii=False))
        return
    if opt.json:
        print(json.dumps({"positionen": tabelle, "lehren": zaehler, "paare": paare},
                         ensure_ascii=False, indent=2))
        return
    print(f"{len(berichte)} Durchgänge\n")
    print("Bed./Pos  n  Erfolg 1.V.  OK-Anteil 1.V.  Versuche  bestanden  mit Gedächtnis  Modellzeit s")
    for schluessel, k in tabelle.items():
        zeit = "–" if k["modellzeit_bis_bestanden_s"] is None else f"{k['modellzeit_bis_bestanden_s']:.1f}"
        print(f"{schluessel:<9}{k['n']:>2}  {k['erfolg_erster_versuch']:>10.0%}  "
              f"{k['anteil_ok_erster_versuch']:>13.0%}  {k['versuche']:>8.2f}  "
              f"{k['bestanden']:>9.0%}  {k['mit_gedaechtnis']:>14.0%}  {zeit:>12}")
    print("\nPaarvergleich späte Positionen (4-6), Differenz zu A in Prozentpunkten:")
    for p in paare:
        teile = [f"{k} {v * 100:+.0f}" for k, v in p.items() if k not in ("folge", "seed")]
        print(f"  Reihenfolge {p['folge']}, Seed {p['seed']}: " + ", ".join(teile))
    print()
    for bedingung, z in sorted(zaehler.items()):
        print(f"Lehren {bedingung}: " + ", ".join(f"{k} {v}" for k, v in z.items()))


if __name__ == "__main__":
    main()
