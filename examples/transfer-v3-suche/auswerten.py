#!/usr/bin/env python3
"""Auswertung der Aufgabensuche für Transfer v3. Reine Vorauswahl: keine Rate, keine
Wirksamkeitsaussage.

Stufe o (je Aufgabe 2 Läufe ohne Hilfe):
- geeignet, wenn kein Lauf technisch ausgefallen ist, die Zielprüfung in mindestens einem
  Lauf „verfehlt“ ist (Falle mit erreichter Vorbedingung tatsächlich beobachtet) und die
  übrigen Prüfungen über beide Läufe zusammen mindestens 80 % bestehen (Nenner: 2 × Anzahl
  übriger Prüfungen; „nicht beobachtbar“ zählt mit, technisch ausgefallene Läufe schließen
  die Aufgabe aus).
- Rang: zuerst gemischt (1 bestanden, 1 verfehlt), dann ohne bestandenen Lauf; bei
  Gleichstand die feste Reihenfolge aus aufgaben.REIHENFOLGE.
- Auswahl für Stufe d: die ersten höchstens 3 geeigneten.

Stufe d (je ausgewählte Aufgabe 1 Lauf mit direkter Hilfe): bestätigt, wenn nicht technisch
ausgefallen, Zielprüfung bestanden und übrige Prüfungen mindestens 80 %.
"""

import json
import sys
from pathlib import Path

import aufgaben
from werkzeuge import plan_laden, zeitplan

HINWEIS = "Vorauswahl aus 2 + 1 Läufen je Aufgabe; keine Rate, keine Wirksamkeitsaussage."


def laden(ordner):
    ordner = Path(ordner)
    einstellungen = json.loads((ordner / "einstellungen.json").read_text(encoding="utf-8"))
    ergebnisse = [json.loads(p.read_text(encoding="utf-8"))
                  for p in sorted(ordner.glob("*/ergebnis.json"))]
    return einstellungen, ergebnisse


def vollstaendig(laeufe, ergebnisse):
    """Probleme, wenn Ergebnisse fehlen, doppelt sind oder nicht zum Zeitplan passen."""
    erwartet = {(l["nr"], l["aufgabe"], l["bedingung"], l["seed"]) for l in laeufe}
    gefunden = [(e["nr"], e["aufgabe"], e["bedingung"], e["seed"]) for e in ergebnisse]
    probleme = []
    if len(gefunden) != len(set(gefunden)):
        probleme.append("doppelte Ergebnisse")
    if set(gefunden) - erwartet:
        probleme.append(f"unerwartete Läufe: {sorted(set(gefunden) - erwartet)}")
    if erwartet - set(gefunden):
        probleme.append(f"fehlende Läufe: {sorted(erwartet - set(gefunden))}")
    return probleme


def kandidat(ergebnisse, plan):
    technisch = sum(e["technischer_fehler"] is not None for e in ergebnisse)
    zaehlung = {s: sum(e["zielstatus"] == s for e in ergebnisse)
                for s in ("bestanden", "verfehlt", "nicht_beobachtbar")}
    uebrige_ok = sum(e["uebrige_ok"] for e in ergebnisse)
    uebrige_von = sum(e["uebrige_von"] for e in ergebnisse)
    rest_ok = uebrige_von > 0 and uebrige_ok / uebrige_von >= plan["regel"]["uebrige_min_anteil"]
    geeignet = technisch == 0 and zaehlung["verfehlt"] >= 1 and rest_ok
    return {"laeufe": len(ergebnisse), **zaehlung, "technisch": technisch,
            "uebrige_ok": uebrige_ok, "uebrige_von": uebrige_von, "uebrige_ausreichend": rest_ok,
            "geeignet": geeignet, "gemischt": zaehlung["bestanden"] == 1 and zaehlung["verfehlt"] == 1}


def o_auswerten(einstellungen, ergebnisse, plan=None):
    plan = plan or plan_laden()
    probleme = vollstaendig(zeitplan("o", plan), ergebnisse)
    if einstellungen.get("stufe") != "o":
        probleme.append("Ordner gehört nicht zu Stufe o")
    kandidaten = {n: kandidat([e for e in ergebnisse if e["aufgabe"] == n], plan)
                  for n in aufgaben.REIHENFOLGE}
    geeignet = [n for n in aufgaben.REIHENFOLGE if kandidaten[n]["geeignet"]]
    rang = sorted(geeignet, key=lambda n: (not kandidaten[n]["gemischt"],
                                           aufgaben.REIHENFOLGE.index(n)))
    gueltig = not probleme
    return {"stufe": "o", "gueltig": gueltig, "probleme": probleme,
            "commit": einstellungen.get("commit"), "attrappe": einstellungen.get("attrappe"),
            "kandidaten": kandidaten, "rang": rang,
            "auswahl": rang[:plan["regel"]["d_hoechstens"]] if gueltig else [],
            "hinweis": HINWEIS}


def d_auswerten(o_bericht, einstellungen, ergebnisse, plan=None):
    plan = plan or plan_laden()
    probleme = [] if o_bericht["gueltig"] else ["Stufe o ungültig"]
    if einstellungen.get("stufe") != "d":
        probleme.append("Ordner gehört nicht zu Stufe d")
    if einstellungen.get("commit") != o_bericht["commit"]:
        probleme.append("Stufe d stammt von einem anderen Commit als Stufe o")
    if einstellungen.get("auswahl") != o_bericht["auswahl"]:
        probleme.append("Auswahl in Stufe d weicht von der Auswertung der Stufe o ab")
    probleme += vollstaendig(zeitplan("d", plan, o_bericht["auswahl"]), ergebnisse)
    minimum = plan["regel"]["uebrige_min_anteil"]
    bestaetigt, laeufe = [], {}
    for e in ergebnisse:
        ok = (e["technischer_fehler"] is None and e["zielstatus"] == "bestanden"
              and e["uebrige_von"] > 0 and e["uebrige_ok"] / e["uebrige_von"] >= minimum)
        laeufe[e["aufgabe"]] = {"zielstatus": e["zielstatus"], "technisch": e["technischer_fehler"] is not None,
                                "uebrige_ok": e["uebrige_ok"], "uebrige_von": e["uebrige_von"],
                                "bestaetigt": ok}
    if not probleme:
        bestaetigt = [n for n in o_bericht["auswahl"] if laeufe.get(n, {}).get("bestaetigt")]
    return {"stufe": "d", "gueltig": not probleme, "probleme": probleme, "laeufe": laeufe,
            "bestaetigt": bestaetigt, "hinweis": HINWEIS}


def main(argumente):
    if len(argumente) not in (2, 3):
        print("Aufruf: auswerten.py O_ORDNER [D_ORDNER]", file=sys.stderr)
        return 2
    bericht = {"o": o_auswerten(*laden(argumente[1]))}
    if len(argumente) == 3:
        bericht["d"] = d_auswerten(bericht["o"], *laden(argumente[2]))
    print(json.dumps(bericht, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
