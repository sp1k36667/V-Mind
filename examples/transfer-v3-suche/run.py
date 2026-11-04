#!/usr/bin/env python3
"""Host der Aufgabensuche für Transfer v3: Gemma 4 12B löst je Lauf eine Aufgabe im ersten
Versuch.

Stufe o: 6 Aufgaben × 2 Seeds ohne Hilfe (12 Aufrufe). Stufe d: höchstens 3 nach der
vorab festgelegten Regel ausgewählte Aufgaben mit direkter Hilfe (höchstens 3 Aufrufe).
Harte Grenze: 15 Generierungsanfragen je Ausgabeordner, gezählt vor dem Senden, also auch
fehlgeschlagene. Kein Lauf wird wiederholt; ein unvollständiger Laufordner stoppt den Host.
Plan: docs/experiments/transfer-v3-suche-plan.md. Reine Vorauswahl, keine Wirksamkeitsaussage.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import aufgaben
import auswerten
import referenz
from werkzeuge import (BASIS, abnahme_ausfuehren, abnahme_einrichten, plan_laden, tests,
                       zeitplan, zielstatus)

OLLAMA = "http://127.0.0.1:11434"
HTTP_ZEITLIMIT = 600
MAX_ZEILEN = 150
PROTOKOLL = "aufrufe.jsonl"

SYSTEM = f"""Du schreibst Python-Programme. Antworte ausschließlich mit dem vollständigen
Inhalt der Datei app.py, ohne Markdown und ohne Erklärungen. Höchstens {MAX_ZEILEN} Zeilen.
Setze das Gerüst aus "geruest" vollständig um; Klassen-, Funktions- und Methodennamen und
Parameter bleiben unverändert."""


def prompt(name, bedingung, plan):
    text = aufgaben.spezifikation(name)
    if bedingung == "D":
        text += "\n\n" + plan["direkte_anweisung"][name]
    return json.dumps({"aufgabe": text, "geruest": aufgaben.geruest(name), "zieldatei": "app.py"},
                      ensure_ascii=False)


def anfrage(pfad, nutzlast, zeitlimit=HTTP_ZEITLIMIT):
    req = urllib.request.Request(OLLAMA + pfad, data=json.dumps(nutzlast).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=zeitlimit) as antwort:
        return json.load(antwort)


def modell_pruefen(plan):
    with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=30) as antwort:
        modelle = {m["name"]: m["digest"] for m in json.load(antwort)["models"]}
    if modelle.get(plan["modell"]) != plan["modell_digest"]:
        raise SystemExit(f"Modell {plan['modell']} fehlt oder hat einen anderen Digest; Abbruch.")


def git_stand():
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=BASIS, capture_output=True,
                            text=True, check=True).stdout.strip()
    sauber = not subprocess.run(["git", "status", "--porcelain", "--", "."], cwd=BASIS,
                                capture_output=True, text=True, check=True).stdout.strip()
    return commit, sauber


class Modell:
    @staticmethod
    def anfrage_bauen(lauf, plan):
        return {"model": plan["modell"], "system": SYSTEM,
                "prompt": prompt(lauf["aufgabe"], lauf["bedingung"], plan), "stream": False,
                "think": plan["think"], "options": {**plan["optionen"], "seed": lauf["seed"]}}

    @staticmethod
    def senden(nutzlast, lauf):
        anfrage("/api/generate", {"model": nutzlast["model"], "keep_alive": 0}, 120)
        return anfrage("/api/generate", nutzlast)


class Attrappe:
    """Ohne Modell, nur zum Prüfen von Host und Auswertung; nie Messdaten. Unter O bei
    Aufgaben mit geradem Index gemischt (erster Seed korrekt, zweiter Falle), sonst zweimal
    Falle; unter D korrekt."""

    @staticmethod
    def anfrage_bauen(lauf, plan):
        return {"attrappe": True, "prompt": prompt(lauf["aufgabe"], lauf["bedingung"], plan)}

    @staticmethod
    def senden(nutzlast, lauf):
        plan = plan_laden()
        index = aufgaben.REIHENFOLGE.index(lauf["aufgabe"])
        korrekt = lauf["bedingung"] == "D" or (
            index % 2 == 0 and lauf["seed"] == plan["stufen"]["o"]["seeds"][0])
        return {"response": referenz.quelltext(lauf["aufgabe"], None if korrekt else "falle"),
                "done": True, "done_reason": "stop"}


def code_aus_antwort(text):
    code = text.strip()
    if code.startswith("```"):
        code = code.split("\n", 1)[-1].rsplit("```", 1)[0].rstrip()
    return code


def protokoll_lesen(wurzel):
    pfad = wurzel / PROTOKOLL
    if not pfad.exists():
        return []
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def aufruf_anmelden(wurzel, stufe, lauf, plan):
    """Zählt die Anfrage vor dem Senden. Verweigert, wenn die Grenze erreicht ist oder
    derselbe Lauf schon angemeldet war (keine Wiederholung)."""
    frueher = protokoll_lesen(wurzel)
    if any(e["stufe"] == stufe and e["nr"] == lauf["nr"] for e in frueher):
        raise SystemExit(f"Lauf {stufe}/{lauf['nr']} wurde bereits gesendet; keine Wiederholung.")
    if len(frueher) >= plan["regel"]["max_aufrufe"]:
        raise SystemExit(f"Grenze von {plan['regel']['max_aufrufe']} Aufrufen erreicht; Abbruch.")
    eintrag = {"stufe": stufe, **lauf, "zeit": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    with (wurzel / PROTOKOLL).open("a", encoding="utf-8") as datei:
        datei.write(json.dumps(eintrag, ensure_ascii=False) + "\n")


def lauf_ausfuehren(lauf, ordner, plan, quelle, anmelden):
    ordner.mkdir(parents=True)
    abnahme_einrichten(lauf["aufgabe"], ordner)
    ergebnis = {**lauf, "technischer_fehler": None}
    start = time.time()
    nutzlast = quelle.anfrage_bauen(lauf, plan)
    anmelden()
    try:
        antwort = quelle.senden(nutzlast, lauf)
    except (OSError, ValueError) as fehler:
        ergebnis["technischer_fehler"] = f"{type(fehler).__name__}: {fehler}"
        antwort = {}
    (ordner / "generierung.json").write_text(
        json.dumps({"anfrage": nutzlast, "antwort": antwort}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    abgeschnitten = bool(antwort) and (not antwort.get("done") or antwort.get("done_reason") == "length")
    if abgeschnitten and ergebnis["technischer_fehler"] is None:
        ergebnis["technischer_fehler"] = "abgeschnittene Antwort"
    code = "" if abgeschnitten else code_aus_antwort(antwort.get("response", ""))
    (ordner / "app.py").write_text(code + "\n", encoding="utf-8")
    abnahme = abnahme_ausfuehren(ordner)
    (ordner / "abnahme.txt").write_text(abnahme["ausgabe"], encoding="utf-8")
    rollen = tests(lauf["aufgabe"])
    status = {t: abnahme["status"].get(t, "ERROR")
              for t in [rollen["ziel"], *rollen["diagnose"], *rollen["uebrige"]]}
    ergebnis.update({
        "zielstatus": zielstatus(abnahme), "status": status, "abbruch": abnahme["abbruch"],
        "uebrige_ok": sum(status[t] == "ok" for t in rollen["uebrige"]),
        "uebrige_von": len(rollen["uebrige"]),
        "diagnose": {t: status[t] for t in rollen["diagnose"]},
        "abgeschnitten": abgeschnitten, "code_zeilen": len(code.splitlines()),
        "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
        "ausgabe_tokens": antwort.get("eval_count"), "prompt_tokens": antwort.get("prompt_eval_count"),
        "dauer_s": round(time.time() - start, 1),
    })
    (ordner / "ergebnis.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
    return ergebnis


def auswahl_aus_o(wurzel, commit, attrappe):
    """Stufe d nur nach gültiger Stufe o desselben Commits und derselben Betriebsart."""
    bericht = auswerten.o_auswerten(*auswerten.laden(wurzel / "o"))
    if bericht["commit"] != commit or bericht["attrappe"] != attrappe:
        raise SystemExit("Stufe o stammt nicht von diesem Commit oder passt nicht zur Betriebsart.")
    if not bericht["gueltig"]:
        raise SystemExit(f"Stufe o ist ungültig: {bericht['probleme']}")
    return bericht["auswahl"]


def einstellungen_sichern(ordner, aktuell):
    pfad = ordner / "einstellungen.json"
    if pfad.exists():
        frueher = json.loads(pfad.read_text(encoding="utf-8"))
        if {k: frueher.get(k) for k in aktuell} != aktuell:
            raise SystemExit("Ausgabeordner gehört zu anderem Stand oder anderer Stufe; Abbruch.")
    else:
        pfad.write_text(json.dumps(aktuell, ensure_ascii=False, indent=1), encoding="utf-8")


def stufe_ausfuehren(wurzel, stufe, plan, quelle, commit, sauber, attrappe):
    auswahl = auswahl_aus_o(wurzel, commit, attrappe) if stufe == "d" else None
    laeufe = zeitplan(stufe, plan, auswahl)
    ordner = wurzel / stufe
    ordner.mkdir(parents=True, exist_ok=True)
    einstellungen_sichern(ordner, {
        "stufe": stufe, "commit": commit, "sauber": sauber, "attrappe": attrappe,
        "plan_sha256": hashlib.sha256((BASIS / "bedingungen.json").read_bytes()).hexdigest(),
        "system_sha256": hashlib.sha256(SYSTEM.encode()).hexdigest(),
        "auswahl": auswahl, "laeufe": laeufe})
    if stufe == "d" and not laeufe:
        print("Keine Aufgabe geeignet; keine Läufe mit direkter Hilfe.")
    for lauf in laeufe:
        laufordner = ordner / f"{lauf['nr']:02d}-{lauf['aufgabe']}-{lauf['bedingung']}-s{lauf['seed']}"
        if (laufordner / "ergebnis.json").exists():
            gespeichert = json.loads((laufordner / "ergebnis.json").read_text(encoding="utf-8"))
            if {k: gespeichert.get(k) for k in lauf} != lauf:
                raise SystemExit(f"{laufordner.name}: gespeichertes Ergebnis passt nicht zum Zeitplan.")
            continue
        if laufordner.exists():
            raise SystemExit(f"{laufordner.name} ist unvollständig; nicht still wiederholen, erst prüfen.")
        e = lauf_ausfuehren(lauf, laufordner, plan, quelle,
                            lambda l=lauf: aufruf_anmelden(wurzel, stufe, l, plan))
        print(f"{laufordner.name}: Ziel {e['zielstatus']}, übrige {e['uebrige_ok']}/{e['uebrige_von']}"
              f"{', technischer Fehler' if e['technischer_fehler'] else ''}", flush=True)
    print("Fertig.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stufe", required=True, choices=("o", "d"))
    parser.add_argument("--ausgabe", required=True, type=Path,
                        help="gemeinsamer Ordner beider Stufen (enthält o/, d/ und aufrufe.jsonl)")
    parser.add_argument("--attrappe", action="store_true",
                        help="ohne Modell mit Referenzlösungen; prüft nur Host und Auswertung")
    opt = parser.parse_args()
    plan = plan_laden()
    commit, sauber = git_stand()
    if not opt.attrappe:
        if not sauber:
            raise SystemExit("examples/transfer-v3-suche hat uneingecheckte Änderungen; gezählte Läufe nur am eingefrorenen Commit.")
        modell_pruefen(plan)
    opt.ausgabe.mkdir(parents=True, exist_ok=True)
    stufe_ausfuehren(opt.ausgabe, opt.stufe, plan, Attrappe if opt.attrappe else Modell,
                     commit, sauber, opt.attrappe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
