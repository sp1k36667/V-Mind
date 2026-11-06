#!/usr/bin/env python3
"""Host von R1: Gemma 4 12B repariert archivierte Erstlösungen in drei Armen (O, P, L).

Vorbereitung ohne Modell (faelle.json, wissen.db, abruf.json) und danach höchstens 108
Generierungen, jede vor dem Senden in aufrufe.jsonl angemeldet (auch fehlgeschlagene). Kein Lauf
wird wiederholt; ein unvollständiger Laufordner stoppt den Host. Gezählte Läufe nur am sauberen,
eingefrorenen Commit. Plan: docs/experiments/r1-plan.md.

Aufruf: r1_host.py --ausgabe ORDNER [--attrappe] [--vmind PROGRAMM]
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import r1_wissen
import r1_werkzeuge as w

PROTOKOLL = "aufrufe.jsonl"


def git_stand():
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=w.BASIS, capture_output=True, text=True,
                            check=True).stdout.strip()
    sauber = not subprocess.run(["git", "status", "--porcelain", "--", str(w.BASIS), str(w.PILOT)],
                                cwd=w.BASIS, capture_output=True, text=True, check=True).stdout.strip()
    return commit, sauber


def datei_sha(pfad):
    return hashlib.sha256(Path(pfad).read_bytes()).hexdigest()


def sichern(pfad, inhalt):
    """Schreibt inhalt als JSON; existiert die Datei, muss sie gleich sein."""
    pfad = Path(pfad)
    if pfad.exists():
        if json.loads(pfad.read_text(encoding="utf-8")) != inhalt:
            raise SystemExit(f"{pfad.name} weicht von der Neuberechnung ab; Abbruch.")
        return
    pfad.write_text(json.dumps(inhalt, ensure_ascii=False, indent=1), encoding="utf-8")


def abruf_vorbereiten(faelle, db, plan, programm):
    texte = w.prompttexte()
    ergebnis = {}
    for fall in faelle:
        abnahme_text = (w.REPO / fall["ordner"] / "abnahme.txt").read_text(encoding="utf-8", errors="replace")
        anfrage = w.anfrage(abnahme_text, plan)
        roh = w.abruf_jsonl(db, anfrage, plan, programm)
        l_ids = [t["id"] for t in roh if w.passend(t, abnahme_text)][:plan["abruf"]["max_hinweise"]]
        p_ids = w.p_zuteilen(l_ids, plan, texte)
        ergebnis[str(fall["fall"])] = {
            "anfrage": anfrage, "roh": [t["id"] for t in roh], "l_ids": l_ids, "p_ids": p_ids,
            "klasse": w.abruf_klasse(l_ids, fall["familie"], plan),
            "gedaechtnis": {"O": [], "L": [w.hinweis(i, plan, texte) for i in l_ids],
                            "P": [w.hinweis(i, plan, texte) for i in p_ids]}}
    return ergebnis


def protokoll_lesen(wurzel):
    pfad = Path(wurzel) / PROTOKOLL
    if not pfad.exists():
        return []
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def aufruf_anmelden(wurzel, lauf, plan):
    frueher = protokoll_lesen(wurzel)
    if any(e["nr"] == lauf["nr"] for e in frueher):
        raise SystemExit(f"Lauf {lauf['nr']} wurde bereits gesendet; keine Wiederholung.")
    if len(frueher) >= plan["max_aufrufe"]:
        raise SystemExit(f"Grenze von {plan['max_aufrufe']} Aufrufen erreicht; Abbruch.")
    with (Path(wurzel) / PROTOKOLL).open("a", encoding="utf-8") as datei:
        datei.write(json.dumps({**lauf, "zeit": time.strftime("%Y-%m-%dT%H:%M:%S%z")}) + "\n")


class Modell:
    @staticmethod
    def senden(lauf, fall, prompt_text, plan):
        pilot_plan = w.pilot_plan()
        nutzlast = {"model": plan["modell"], "system": w.pilot.SYSTEM, "prompt": prompt_text, "stream": False,
                    "think": plan["think"], "options": {**plan["optionen"], "seed": lauf["seed"]}}
        w.pilot.anfrage("/api/generate", {"model": plan["modell"], "keep_alive": 0}, 120)
        assert pilot_plan["modell"] == plan["modell"]
        return nutzlast, w.pilot.anfrage("/api/generate", nutzlast)


class Attrappe:
    """Ohne Modell, nur für Host und Auswertung; nie Messdaten. O und P geben den bisherigen
    Code unverändert zurück, L bei richtigem Abruf die Referenzlösung des Pilots."""

    abruf = {}

    @classmethod
    def senden(cls, lauf, fall, prompt_text, plan):
        if lauf["arm"] == "L" and cls.abruf[str(fall["fall"])]["klasse"] == "richtig":
            basis = (w.REFERENZ / "basis.py").read_text(encoding="utf-8")
            app = (w.REFERENZ / f"{fall['aufgabe']}.py").read_text(encoding="utf-8")
            code = basis + "\n\n" + app.replace("from basis import", "# basis eingebettet:\n# from basis import")
        else:
            code = (w.REPO / fall["ordner"] / "app.py").read_text(encoding="utf-8")
        return {"attrappe": True}, {"response": code, "done": True, "done_reason": "stop"}


def auswerten_lauf(fall, abnahme):
    tests = w.alle_tests(fall["aufgabe"])
    status = {t: abnahme["status"].get(t) for t in tests}
    vollstaendig = abnahme["abbruch"] is None and all(v is not None for v in status.values())
    vorher = fall["status_vorher"]
    return {"status": status, "repariert": vollstaendig and all(v == "ok" for v in status.values()),
            "behoben": [t for t in fall["nicht_ok"] if status.get(t) == "ok"],
            "regression": None if not vollstaendig else [t for t, v in vorher.items() if v == "ok" and status.get(t) != "ok"],
            "abnahme_vollstaendig": vollstaendig}


def lauf_ausfuehren(lauf, fall, gedaechtnis, ordner, plan, quelle, wurzel):
    ordner.mkdir(parents=True)
    w.abnahme_einrichten(fall["aufgabe"], ordner)
    prompt_text = w.prompt(fall, gedaechtnis, plan)
    ergebnis = {**lauf, "technischer_fehler": None, "gedaechtnis_eintraege": len(gedaechtnis)}
    start = time.time()
    aufruf_anmelden(wurzel, lauf, plan)
    try:
        nutzlast, antwort = quelle.senden(lauf, fall, prompt_text, plan)
    except (OSError, ValueError) as fehler:
        nutzlast, antwort = {}, {}
        ergebnis["technischer_fehler"] = f"{type(fehler).__name__}: {fehler}"
    (ordner / "generierung.json").write_text(json.dumps({"prompt": prompt_text, "anfrage": nutzlast,
                                                         "antwort": antwort}, ensure_ascii=False), encoding="utf-8")
    if not ergebnis["technischer_fehler"]:
        if not antwort.get("done") or antwort.get("done_reason") != "stop":
            ergebnis["technischer_fehler"] = f"done_reason {antwort.get('done_reason')}"
        elif not antwort.get("response", "").strip():
            ergebnis["technischer_fehler"] = "leere Antwort"
    code = "" if ergebnis["technischer_fehler"] else w.pilot.code_aus_antwort(antwort.get("response", ""))
    (ordner / "app.py").write_text(code + "\n", encoding="utf-8")
    abnahme = w.abnahme_ausfuehren(ordner)
    (ordner / "abnahme.txt").write_text(abnahme["ausgabe"], encoding="utf-8")
    ergebnis.update(auswerten_lauf(fall, abnahme))
    if ergebnis["technischer_fehler"]:
        ergebnis["repariert"] = False
    ergebnis.update({"dauer_s": round(time.time() - start, 1), "ausgabe_tokens": antwort.get("eval_count"),
                     "prompt_tokens": antwort.get("prompt_eval_count"), "code_zeilen": len(code.splitlines())})
    (ordner / "ergebnis.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")
    return ergebnis


def vorbereiten(wurzel, plan, programm):
    auswahl = w.faelle_bestimmen(plan)
    sichern(wurzel / "faelle.json", auswahl)
    db = wurzel / "wissen.db"
    if not db.exists():
        r1_wissen.aufbauen(db, programm)
    abruf = abruf_vorbereiten(auswahl["faelle"], db, plan, programm)
    sichern(wurzel / "abruf.json", abruf)
    return auswahl["faelle"], abruf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ausgabe", required=True, type=Path)
    parser.add_argument("--attrappe", action="store_true")
    parser.add_argument("--vmind", default="vmind", help="vmind-Programm für Wissensbestand und recall")
    opt = parser.parse_args()
    plan = w.plan_laden()
    commit, sauber = git_stand()
    if not opt.attrappe:
        if not sauber:
            raise SystemExit("examples/r1 oder examples/transfer hat uneingecheckte Änderungen; gezählte Läufe nur am Freeze.")
        w.pilot.modell_pruefen(plan)
    opt.ausgabe.mkdir(parents=True, exist_ok=True)
    faelle, abruf = vorbereiten(opt.ausgabe, plan, opt.vmind)
    laeufe = w.zeitplan(faelle, plan)
    if len(laeufe) != plan["max_aufrufe"]:
        raise SystemExit(f"{len(laeufe)} Läufe geplant statt {plan['max_aufrufe']}.")
    sichern(opt.ausgabe / "einstellungen.json", {
        "commit": commit, "sauber": sauber, "attrappe": opt.attrappe,
        "plan_sha256": datei_sha(w.BASIS / "bedingungen.json"),
        "prompttexte_sha256": datei_sha(w.BASIS / "wissen" / "prompttexte.json"),
        "eintraege_sha256": datei_sha(w.BASIS / "wissen" / "eintraege.json"),
        "system_sha256": hashlib.sha256(w.pilot.SYSTEM.encode()).hexdigest(), "laeufe": laeufe})
    quelle = Attrappe if opt.attrappe else Modell
    Attrappe.abruf = abruf
    nach_fall = {f["fall"]: f for f in faelle}
    for lauf in laeufe:
        ordner = opt.ausgabe / "laeufe" / f"{lauf['nr']:03d}-f{lauf['fall']:02d}-{lauf['aufgabe']}-{lauf['arm']}"
        if (ordner / "ergebnis.json").exists():
            gespeichert = json.loads((ordner / "ergebnis.json").read_text(encoding="utf-8"))
            if {k: gespeichert.get(k) for k in lauf} != lauf:
                raise SystemExit(f"{ordner.name}: gespeichertes Ergebnis passt nicht zum Zeitplan.")
            continue
        if ordner.exists():
            raise SystemExit(f"{ordner.name} ist unvollständig; nicht still wiederholen, erst prüfen.")
        gedaechtnis = abruf[str(lauf["fall"])]["gedaechtnis"][lauf["arm"]]
        e = lauf_ausfuehren(lauf, nach_fall[lauf["fall"]], gedaechtnis, ordner, plan, quelle, opt.ausgabe)
        print(f"{ordner.name}: {'repariert' if e['repariert'] else 'nicht repariert'}"
              f"{', technisch' if e['technischer_fehler'] else ''}", flush=True)
    print("Fertig.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
