#!/usr/bin/env python3
"""Auswertung von R1 nach docs/experiments/r1-plan.md. Pilot: Erfolg heißt nur „über den
vorläufigen Schwellen“, keine Bestätigung eines spezifischen Effekts.

Aufruf: r1_auswerten.py ORDNER
"""

import json
import math
import sys
from collections import Counter
from pathlib import Path

import r1_werkzeuge as w


def mcnemar_einseitig(b, c):
    n = b + c
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(b, n + 1)) / 2 ** n


def laden(ordner):
    ordner = Path(ordner)
    lies = lambda name: json.loads((ordner / name).read_text(encoding="utf-8"))
    ergebnisse = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((ordner / "laeufe").glob("*/ergebnis.json"))]
    return lies("einstellungen.json"), lies("faelle.json"), lies("abruf.json"), ergebnisse


def pruefen(einstellungen, ergebnisse, plan):
    probleme = []
    geplant = {(l["nr"], l["fall"], l["arm"]) for l in einstellungen["laeufe"]}
    gefunden = [(e["nr"], e["fall"], e["arm"]) for e in ergebnisse]
    if len(gefunden) != len(set(gefunden)):
        probleme.append("doppelte Läufe")
    if set(gefunden) - geplant:
        probleme.append("unerwartete Läufe")
    if geplant - set(gefunden):
        probleme.append(f"fehlende Läufe: {len(geplant - set(gefunden))}")
    technisch = sum(e["technischer_fehler"] is not None for e in ergebnisse)
    if technisch > plan["kriterien"]["technisch_hoechstens"] / 100 * plan["max_aufrufe"]:
        probleme.append(f"{technisch} technische Ausfälle (mehr als {plan['kriterien']['technisch_hoechstens']} %)")
    return probleme, technisch


def arm_kennzahlen(eintraege, n):
    reg = sum(1 for e in eintraege if e["regression"])
    unbekannt = sum(1 for e in eintraege if e["regression"] is None)
    erfolge = sum(e["repariert"] for e in eintraege)
    dauer = sum(e.get("dauer_s") or 0 for e in eintraege)
    tokens = sum(e.get("ausgabe_tokens") or 0 for e in eintraege)
    return {"repariert": erfolge, "von": n, "anteil": erfolge / n, "regression": reg,
            "regression_unbekannt": unbekannt, "technisch": sum(e["technischer_fehler"] is not None for e in eintraege),
            "dauer_s": round(dauer, 1), "ausgabe_tokens": tokens,
            "dauer_je_reparatur_s": round(dauer / erfolge, 1) if erfolge else None}


def auswerten(einstellungen, faelle_daten, abruf, ergebnisse, plan=None):
    plan = plan or w.plan_laden()
    probleme, technisch = pruefen(einstellungen, ergebnisse, plan)
    faelle = {f["fall"]: f for f in faelle_daten["faelle"]}
    n = len(faelle)
    je = {arm: {e["fall"]: e for e in ergebnisse if e["arm"] == arm} for arm in plan["arme"]}
    kennzahlen = {arm: arm_kennzahlen(list(je[arm].values()), n) for arm in plan["arme"]}
    b = sum(1 for f in faelle if je["L"].get(f, {}).get("repariert") and not je["O"].get(f, {}).get("repariert"))
    c = sum(1 for f in faelle if je["O"].get(f, {}).get("repariert") and not je["L"].get(f, {}).get("repariert"))
    p_wert = mcnemar_einseitig(b, c)
    k = plan["kriterien"]
    anteil = lambda arm: kennzahlen[arm]["anteil"]
    reg = lambda arm, streng=False: (kennzahlen[arm]["regression"]
                                     + (kennzahlen[arm]["regression_unbekannt"] if streng else 0)) / n
    kriterien = {
        "l_minus_o": {"wert_pp": round(100 * (anteil("L") - anteil("O")), 1), "erfuellt": anteil("L") - anteil("O") >= k["l_minus_o_pp"] / 100},
        "mcnemar": {"b": b, "c": c, "p": round(p_wert, 4), "erfuellt": p_wert < k["alpha"]},
        "l_minus_p": {"wert_pp": round(100 * (anteil("L") - anteil("P")), 1), "erfuellt": anteil("L") - anteil("P") >= k["l_minus_p_pp"] / 100},
        "regression": {"haupt_pp": round(100 * (reg("L") - reg("O")), 1),
                       "sensitiv_pp": round(100 * (reg("L", True) - reg("O")), 1),
                       "erfuellt": reg("L") - reg("O") <= k["regression_pp"] / 100
                       and reg("L", True) - reg("O") <= k["regression_pp"] / 100},
    }
    nicht_leer = [f for f in faelle if abruf[str(f)]["l_ids"]]
    beschreibend = {
        "abruf": dict(Counter(abruf[str(f)]["klasse"] for f in faelle)),
        "abruf_je_familie": {fam: dict(Counter(abruf[str(f)]["klasse"] for f in faelle if faelle[f]["familie"] == fam))
                             for fam in sorted({x["familie"] for x in faelle.values()})},
        "l_minus_p_nicht_leer": {"faelle": len(nicht_leer),
                                 "L": sum(je["L"].get(f, {}).get("repariert", False) for f in nicht_leer),
                                 "P": sum(je["P"].get(f, {}).get("repariert", False) for f in nicht_leer)},
        "je_aufgabe": {a: {arm: sum(je[arm].get(f, {}).get("repariert", False) for f in faelle if faelle[f]["aufgabe"] == a)
                           for arm in plan["arme"]} | {"faelle": sum(1 for f in faelle if faelle[f]["aufgabe"] == a)}
                       for a in plan["bewertungsaufgaben"]},
        "je_abrufklasse": {kl: {arm: sum(je[arm].get(f, {}).get("repariert", False) for f in faelle if abruf[str(f)]["klasse"] == kl)
                                for arm in plan["arme"]} for kl in ("richtig", "falsch", "leer")},
    }
    gueltig = not probleme
    return {"gueltig": gueltig, "probleme": probleme, "technisch": technisch,
            "attrappe": einstellungen.get("attrappe"), "commit": einstellungen.get("commit"),
            "kennzahlen": kennzahlen, "kriterien": kriterien,
            "pilot_ueber_schwellen": gueltig and all(x["erfuellt"] for x in kriterien.values()),
            "beschreibend": beschreibend,
            "hinweis": "Pilot mit 36 Fällen; simulierte Trennschärfe 0,56 bei 30 pp, Fehlalarm bis 0,12 bei starkem unspezifischem Effekt."}


def main(argumente):
    if len(argumente) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    print(json.dumps(auswerten(*laden(argumente[1])), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
