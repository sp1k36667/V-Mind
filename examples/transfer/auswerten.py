#!/usr/bin/env python3
"""Auswertung des Transfer-Pilots nach den vorab festgelegten Kriterien.

Aufruf: auswerten.py VORLAUF HAUPT GEGENFALL (je ein Ordner von run.py; Teilmengen erlaubt,
dann gibt es kein Gesamtergebnis). Eine Stufe ist nur gültig, wenn ihre Läufe genau dem
Zeitplan des unveränderten Plans entsprechen (vollständig, ohne Dubletten oder fremde
Läufe) und höchstens 10 % technisch ausfielen (HTTP-Fehler oder abgeschnittene Antwort).
Ungültig oder unvollständig heißt nie bestanden. Technische Ausfälle zählen in allen
Raten als nicht bestanden."""

import hashlib
import json
import sys
from collections import defaultdict
from math import comb
from pathlib import Path

from werkzeuge import BASIS, plan_laden, zeitplan

VORLAUF_HOECHSTENS = 0.60
TECHNISCH_HOECHSTENS = 0.10
MIN_L_UEBER_O_PP = 30
MIN_L_UEBER_P_PP = 20
MIN_AUFGABEN_L_UEBER_O = 3
ALPHA = 0.05
MAX_SCHADEN_PP = 10
MAX_GEGENFALL_MEHR = 1
IDENTITAET = ("nr", "aufgabe", "bedingung", "seed")


def mcnemar_einseitig(b, c):
    """Exakter einseitiger McNemar-Test: P(X >= b) bei X ~ Bin(b + c, 1/2).
    b = Paare mit L bestanden und O nicht, c = umgekehrt."""
    n = b + c
    if n == 0:
        return 1.0
    return sum(comb(n, k) for k in range(b, n + 1)) / 2 ** n


def technisch(e):
    return bool(e["technischer_fehler"]) or bool(e["abgeschnitten"])


def pruefen(stufe, ergebnisse, einstellungen=None):
    """Probleme, die eine Stufe ungültig machen; leer heißt gültig."""
    plan = plan_laden()
    probleme = []
    if einstellungen is not None:
        plan_sha = hashlib.sha256((BASIS / "bedingungen.json").read_bytes()).hexdigest()
        if einstellungen.get("plan_sha256") != plan_sha:
            probleme.append("bedingungen.json seit dem Lauf verändert")
    erwartet = [tuple(l[k] for k in IDENTITAET) for l in zeitplan(stufe, plan)]
    vorhanden = [tuple(e.get(k) for k in IDENTITAET) for e in ergebnisse]
    doppelt = sorted({v for v in vorhanden if vorhanden.count(v) > 1})
    fremd = sorted(set(vorhanden) - set(erwartet))
    fehlend = sorted(set(erwartet) - set(vorhanden))
    if doppelt:
        probleme.append(f"{len(doppelt)} doppelte Läufe")
    if fremd:
        probleme.append(f"{len(fremd)} Läufe nicht im Zeitplan")
    if fehlend:
        probleme.append(f"{len(fehlend)} von {len(erwartet)} geplanten Läufen fehlen")
    ausfaelle = sum(technisch(e) for e in ergebnisse)
    if ausfaelle > TECHNISCH_HOECHSTENS * len(erwartet):
        probleme.append(f"{ausfaelle} technische Ausfälle (über {TECHNISCH_HOECHSTENS:.0%})")
    return probleme


def kennzahlen(ergebnisse):
    je_bedingung = defaultdict(list)
    for e in ergebnisse:
        je_bedingung[e["bedingung"]].append(e)
    return {b: {
        "laeufe": len(l),
        "ziel": sum(e["ziel_bestanden"] for e in l),
        "ziel_anteil": round(sum(e["ziel_bestanden"] for e in l) / len(l), 3),
        "ziel_formatfehler": sum(bool(e.get("ziel_format_fehler")) for e in l),
        "uebrige_ok": sum(e["uebrige_ok"] for e in l),
        "uebrige_von": sum(e["uebrige_von"] for e in l),
        "technisch": sum(technisch(e) for e in l),
        "abbruch_zeit_oder_ausgabe": sum(bool(e.get("abbruch")) for e in l),
    } for b, l in sorted(je_bedingung.items())}


def vorlauf(ergebnisse, einstellungen=None):
    probleme = pruefen("vorlauf", ergebnisse, einstellungen)
    werte = kennzahlen(ergebnisse).get("O", {"laeufe": 0, "ziel_anteil": 1.0})
    return {"gueltig": not probleme, "probleme": probleme, "kennzahlen": werte,
            "weiter": not probleme and werte["ziel_anteil"] <= VORLAUF_HOECHSTENS,
            "regel": f"gültig und Ziel höchstens {VORLAUF_HOECHSTENS:.0%}"}


def haupt(ergebnisse, einstellungen=None):
    probleme = pruefen("haupt", ergebnisse, einstellungen)
    werte = kennzahlen(ergebnisse)
    paare = defaultdict(dict)
    for e in ergebnisse:
        paare[(e["aufgabe"], e["seed"])][e["bedingung"]] = e["ziel_bestanden"]
    b = sum(v.get("L", False) and not v.get("O", False) for v in paare.values())
    c = sum(v.get("O", False) and not v.get("L", False) for v in paare.values())
    rate = {k: 100 * werte.get(k, {"ziel_anteil": 0})["ziel_anteil"] for k in "OLP"}
    je_aufgabe = defaultdict(lambda: {"O": 0, "L": 0, "P": 0})
    for (aufgabe, _), v in paare.items():
        for bedingung, ok in v.items():
            je_aufgabe[aufgabe][bedingung] += ok
    p_wert = mcnemar_einseitig(b, c)

    def uebrige(k):
        w = werte.get(k)
        return 100 * w["uebrige_ok"] / w["uebrige_von"] if w and w["uebrige_von"] else 0.0

    kriterien = {
        "L_ueber_O_pp": round(rate["L"] - rate["O"], 1), "mcnemar_b_c": [b, c],
        "mcnemar_p": round(p_wert, 4), "L_ueber_P_pp": round(rate["L"] - rate["P"], 1),
        "aufgaben_L_ueber_O": sum(v["L"] > v["O"] for v in je_aufgabe.values()),
        "schaden_uebrige_pp": round(uebrige("O") - uebrige("L"), 1),
    }
    erfolg = (not probleme and kriterien["L_ueber_O_pp"] >= MIN_L_UEBER_O_PP and p_wert < ALPHA
              and kriterien["L_ueber_P_pp"] >= MIN_L_UEBER_P_PP
              and kriterien["aufgaben_L_ueber_O"] >= MIN_AUFGABEN_L_UEBER_O)
    return {"gueltig": not probleme, "probleme": probleme, "kennzahlen": werte,
            "je_aufgabe": dict(je_aufgabe), "kriterien": kriterien, "erfolgskriterium": erfolg,
            "schadensgrenze_uebrige": not probleme and kriterien["schaden_uebrige_pp"] <= MAX_SCHADEN_PP}


def gegenfall(ergebnisse, einstellungen=None):
    probleme = pruefen("gegenfall", ergebnisse, einstellungen)
    werte = kennzahlen(ergebnisse)
    fehl = {k: w["laeufe"] - w["ziel"] for k, w in werte.items()}
    return {"gueltig": not probleme, "probleme": probleme, "kennzahlen": werte,
            "fehlschlaege_ziel": fehl,
            "schadensgrenze_gegenfall": not probleme
            and fehl.get("L", 0) - fehl.get("O", 0) <= MAX_GEGENFALL_MEHR,
            "hinweis": "Bei 10 Läufen nur beschreibend, kein Nachweis der Unschädlichkeit; "
                       "Ursache jedes Fehlschlags im Rohcode prüfen."}


STUFEN = {"vorlauf": vorlauf, "haupt": haupt, "gegenfall": gegenfall}


def stufe_auswerten(ordner):
    ordner = Path(ordner)
    einstellungen = json.loads((ordner / "einstellungen.json").read_text(encoding="utf-8"))
    ergebnisse = [json.loads(p.read_text(encoding="utf-8"))
                  for p in sorted(ordner.glob("*/ergebnis.json"))]
    stufe = einstellungen["stufe"]
    bericht = STUFEN[stufe](ergebnisse, einstellungen)
    bericht.update(stufe=stufe, commit=einstellungen["commit"], attrappe=einstellungen["attrappe"])
    return bericht


def gesamt(berichte):
    """Bestanden nur mit allen drei gültigen Stufen am selben Commit, ohne Attrappe."""
    if set(berichte) != set(STUFEN):
        return {"bestanden": False, "grund": "nicht alle Stufen ausgewertet"}
    v, h, g = berichte["vorlauf"], berichte["haupt"], berichte["gegenfall"]
    gruende = []
    if len({b["commit"] for b in berichte.values()}) != 1:
        gruende.append("Stufen von verschiedenen Commits")
    if any(b["attrappe"] for b in berichte.values()):
        gruende.append("Attrappe, keine Messdaten")
    if not (v["gueltig"] and v["weiter"]):
        gruende.append("Vorlauf ungültig oder Gate nicht erfüllt")
    if not h["gueltig"]:
        gruende.append("Hauptlauf ungültig")
    elif not h["erfolgskriterium"]:
        gruende.append("Erfolgskriterium verfehlt")
    if h["gueltig"] and not h["schadensgrenze_uebrige"]:
        gruende.append("Schadensgrenze übrige Prüfungen verletzt")
    if not g["gueltig"]:
        gruende.append("Gegenfall ungültig")
    elif not g["schadensgrenze_gegenfall"]:
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
    print(json.dumps(berichte, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
