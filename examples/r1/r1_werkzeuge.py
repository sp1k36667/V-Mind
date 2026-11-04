"""Gemeinsame Hilfen für R1: Fallauswahl, Fehlerfamilie, Abfrage, Relevanzregel, Arme, Prompt.

Aufgaben, Abnahme und Referenzlösungen stammen unverändert aus dem Transfer-Pilot
(`examples/transfer`). Plan: docs/experiments/r1-plan.md.
"""

import hashlib
import json
import random
import re
import subprocess
import sys
from pathlib import Path

BASIS = Path(__file__).resolve().parent
REPO = BASIS.parent.parent
PILOT = BASIS.parent / "transfer"
sys.path.insert(0, str(PILOT))

import run as pilot  # noqa: E402
from werkzeuge import (REFERENZ, abnahme_ausfuehren, abnahme_einrichten,  # noqa: E402,F401
                       alle_tests)

AUSNAHME = re.compile(r"^(AssertionError|[A-Za-z_]*Error)\b:? ?(.*)$", re.MULTILINE)
TEST_ZEILE = re.compile(r"^(?:FAIL|ERROR): (test_\w+) ", re.MULTILINE)


def plan_laden():
    return json.loads((BASIS / "bedingungen.json").read_text(encoding="utf-8"))


def pilot_plan():
    return json.loads((PILOT / "bedingungen.json").read_text(encoding="utf-8"))


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def familie(abnahme_text, plan):
    for name, muster in plan["familien"]:
        if re.search(muster, abnahme_text):
            return name
    return plan["familie_sonst"]


def kandidaten(plan, aufgaben):
    """Alle archivierten Erstlösungen der Aufgaben unter Bedingung O mit mindestens einer nicht
    bestandenen Prüfung, sortiert nach (Aufgabe, Stufe, Ordnername)."""
    quelle = REPO / plan["quelle"]
    faelle = []
    for pfad in quelle.glob("*/*/ergebnis.json"):
        ergebnis = json.loads(pfad.read_text(encoding="utf-8"))
        if ergebnis["bedingung"] != "O" or ergebnis["aufgabe"] not in aufgaben:
            continue
        nicht_ok = sorted(t for t, v in ergebnis["status"].items() if v != "ok")
        if not nicht_ok:
            continue
        ordner = pfad.parent
        abnahme = (ordner / "abnahme.txt").read_text(encoding="utf-8", errors="replace")
        code = (ordner / "app.py").read_text(encoding="utf-8")
        faelle.append({"aufgabe": ergebnis["aufgabe"], "stufe": ordner.parent.name,
                       "ordner": str(ordner.relative_to(REPO)), "seed_erstlauf": ergebnis["seed"],
                       "familie": familie(abnahme, plan), "nicht_ok": nicht_ok,
                       "status_vorher": ergebnis["status"],
                       "sha_app": sha(code), "sha_abnahme": sha(abnahme)})
    return sorted(faelle, key=lambda f: (f["aufgabe"], f["stufe"], Path(f["ordner"]).name))


def faelle_bestimmen(plan):
    """Bewertungsfälle: sortierte Liste, dann feste Streichung aus der größten Familie."""
    alle = kandidaten(plan, plan["bewertungsaufgaben"])
    regel = plan["auswahl"]
    teil = [f["ordner"] for f in alle if f["familie"] == regel["familie"]]
    gestrichen = set(random.Random(regel["seed"]).sample(teil, regel["streichen"]))
    faelle = [f for f in alle if f["ordner"] not in gestrichen]
    if len(faelle) != regel["faelle"]:
        raise ValueError(f"{len(faelle)} statt {regel['faelle']} Bewertungsfälle")
    for index, fall in enumerate(faelle):
        fall["fall"] = index
        fall["seed"] = plan["fall_seed_basis"] + index
    return {"alle": [f["ordner"] for f in alle], "gestrichen": sorted(gestrichen), "faelle": faelle}


def normalisieren(text):
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", text)).strip()


def ausnahmezeilen(abnahme_text):
    return list(dict.fromkeys(normalisieren(m.group(0)) for m in AUSNAHME.finditer(abnahme_text)))


def anfrage(abnahme_text, plan):
    tests = list(dict.fromkeys(TEST_ZEILE.findall(abnahme_text)))
    text = " ".join(ausnahmezeilen(abnahme_text) + tests)
    return text[:plan["abruf"]["anfrage_max"]]


def tokens(text):
    return set(re.findall(r"\w+", text.lower()))


def bezeichner(meldung):
    """Bezeichner einer Meldung: Wörter in Anführungszeichen und das Wort nach 'attribute'."""
    namen = set(re.findall(r"'([A-Za-z_]\w*)'", meldung))
    namen |= set(re.findall(r"attribute\s+'?([A-Za-z_]\w*)", meldung))
    return {n.lower() for n in namen}


def passend(eintrag, abnahme_text):
    """Relevanzregel (Plan): validiert, error_solution und (a) Ausnahmetyp plus Bezeichner aus
    derselben Meldung als ganze Tokens oder (b) Assertion-Meldung exakt als normalisierter Teiltext."""
    if eintrag.get("status") != "validated" or eintrag.get("kind") != "error_solution":
        return False
    problem = normalisieren(eintrag["problem"])
    woerter = tokens(problem)
    for m in AUSNAHME.finditer(abnahme_text):
        typ, meldung = m.group(1), m.group(2)
        if typ.lower() in woerter and bezeichner(meldung) & woerter:
            return True
        if typ == "AssertionError":
            kern = normalisieren(meldung.split(" : ", 1)[-1])
            if len(kern) >= 8 and kern in problem:
                return True
    return False


def abruf_jsonl(db, anfrage_text, plan, vmind="vmind"):
    """recall über die JSONL-Schnittstelle (installiertes vmind, limit wie im Plan)."""
    zeile = json.dumps({"id": 1, "op": "recall", "query": anfrage_text,
                        "scope": plan["abruf"]["scope"], "limit": plan["abruf"]["limit"]})
    antwort = subprocess.run([vmind, "serve", str(db)], input=zeile + "\n", capture_output=True,
                             text=True, check=True, timeout=60)
    daten = json.loads(antwort.stdout.splitlines()[0])
    if not daten.get("ok"):
        raise RuntimeError(f"recall fehlgeschlagen: {daten}")
    return daten["data"]["memories"]


def prompttexte():
    return {t["id"]: t for t in json.loads((BASIS / "wissen" / "prompttexte.json").read_text(encoding="utf-8"))}


def hinweis(eintrag_id, plan, texte=None):
    t = (texte or prompttexte())[eintrag_id]
    return {"wann": t["wann"][:plan["prompt"]["wann_max"]], "richtig": t["richtig"][:plan["prompt"]["richtig_max"]]}


def abruf_klasse(ids, fall_familie, plan):
    if not ids:
        return "leer"
    familien = {plan["lehrer_familien"].get(str(i)) for i in ids}
    return "richtig" if fall_familie in familien else "falsch"


def p_zuteilen(l_ids, plan, texte=None):
    """P: gleich viele fachfremde Einträge, je L-Hinweis der mit der nächsten Gesamtlänge
    (Gleichstand: kleinere ID), ohne Wiederholung. Leeres L -> leeres P."""
    texte = texte or prompttexte()
    pool = sorted(i for i, t in texte.items() if t["rolle"] == "fachfremd")
    laenge = lambda i: len(hinweis(i, plan, texte)["wann"]) + len(hinweis(i, plan, texte)["richtig"])
    gewaehlt = []
    for l_id in l_ids:
        rest = [i for i in pool if i not in gewaehlt]
        gewaehlt.append(min(rest, key=lambda i: (abs(laenge(i) - laenge(l_id)), i)))
    return gewaehlt


def pruefausgabe(abnahme_text, plan):
    tests = list(dict.fromkeys(TEST_ZEILE.findall(abnahme_text)))
    text = "Fehlgeschlagene Prüfungen: " + ", ".join(tests) + "\n" + "\n".join(ausnahmezeilen(abnahme_text))
    return text[:plan["prompt"]["pruefausgabe_max"]]


AUFTRAG = ("Die bisherige app.py besteht nicht alle Prüfungen. Korrigiere sie und gib die vollständige "
           "korrigierte Datei app.py zurück.")


def prompt(fall, gedaechtnis, plan):
    ordner = REPO / fall["ordner"]
    code = (ordner / "app.py").read_text(encoding="utf-8")
    abnahme_text = (ordner / "abnahme.txt").read_text(encoding="utf-8", errors="replace")
    return json.dumps({"aufgabe": pilot.aufgabentext(fall["aufgabe"], pilot_plan()), "bisheriger_code": code,
                       "pruefausgabe": pruefausgabe(abnahme_text, plan), "auftrag": AUFTRAG,
                       "zieldatei": "app.py", "gedaechtnis": gedaechtnis}, ensure_ascii=False)


def zeitplan(faelle, plan):
    laeufe = [{"fall": f["fall"], "aufgabe": f["aufgabe"], "arm": arm, "seed": f["seed"]}
              for f in faelle for arm in plan["arme"]]
    random.Random(plan["reihenfolge_seed"]).shuffle(laeufe)
    for nummer, lauf in enumerate(laeufe, 1):
        lauf["nr"] = nummer
    return laeufe
