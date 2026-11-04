"""Gemeinsame Hilfen für Host, Selbsttest und Auswertung von Transfer v2."""

import json
import os
import random
import re
import selectors
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import aufgaben

BASIS = Path(__file__).resolve().parent
PRUEFUNG = BASIS / "pruefung"
ABNAHME_ZEITLIMIT = 90
MAX_AUSGABE_BYTES = 200_000
ERGEBNIS = re.compile(r"^(test_\w+) \(.*\) \.\.\. (ok|FAIL|ERROR)", re.MULTILINE)
ZIEL = "test_ziel_mechanismus"


def plan_laden():
    return json.loads((BASIS / "bedingungen.json").read_text(encoding="utf-8"))


def abnahme_einrichten(name, ziel):
    """Kopiert die Abnahme und die Aufgabenbeschreibung nach ZIEL/verification."""
    g, klasse, f1, f2, _ = aufgaben.AUFGABEN[name]
    pruefung = Path(ziel) / "verification"
    pruefung.mkdir(parents=True, exist_ok=True)
    shutil.copy(PRUEFUNG / "abnahme.py", pruefung / "abnahme.py")
    (pruefung / "aufgabe.json").write_text(json.dumps(
        {"name": name, "gruppe": g, "klasse": klasse, "f1": f1, "f2": f2}), encoding="utf-8")


def _gruppe_beenden(prozess):
    try:
        os.killpg(prozess.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def abnahme_ausfuehren(ziel, test=None):
    """Führt die Abnahme ohne Shell aus; Zeit- und Ausgabelimit gelten während der Ausführung,
    bei Überschreitung wird die ganze Prozessgruppe beendet (auch Enkel mit geerbter Pipe).
    Keine Sandbox: Modellcode läuft mit den Rechten des Nutzers, HOME im Arbeitsordner."""
    ziel = Path(ziel)
    befehl = [sys.executable, "verification/abnahme.py"] + ([f"Abnahme.{test}"] if test else [])
    umgebung = {"PATH": os.environ.get("PATH", ""), "HOME": str(ziel), "LANG": "C.UTF-8",
                "PYTHONDONTWRITEBYTECODE": "1"}
    prozess = subprocess.Popen(befehl, cwd=ziel, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, env=umgebung, start_new_session=True)
    gelesen, abbruch = bytearray(), None
    ende = time.monotonic() + ABNAHME_ZEITLIMIT
    os.set_blocking(prozess.stdout.fileno(), False)
    with selectors.DefaultSelector() as auswahl:
        auswahl.register(prozess.stdout, selectors.EVENT_READ)
        offen = True
        while offen or prozess.poll() is None:
            rest = ende - time.monotonic()
            if rest <= 0:
                abbruch = "zeitlimit"
                break
            for key, _ in auswahl.select(timeout=min(rest, 0.05)):
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    auswahl.unregister(prozess.stdout)
                    offen = False
                    continue
                platz = MAX_AUSGABE_BYTES - len(gelesen)
                gelesen.extend(chunk[:max(platz, 0)])
                if len(chunk) > platz:
                    abbruch = "ausgabelimit"
                    break
            if abbruch:
                break
    if abbruch:
        _gruppe_beenden(prozess)
    exit_code = prozess.wait()
    prozess.stdout.close()
    text = bytes(gelesen).decode("utf-8", errors="replace")
    if abbruch:
        text += f"\n[Abbruch: {abbruch}, Prozessgruppe beendet]"
    status = {name: ergebnis for name, ergebnis in ERGEBNIS.findall(text)}
    return {"exit_code": exit_code, "status": status, "ausgabe": text, "abbruch": abbruch}


def _block(ausgabe, test):
    treffer = re.search(rf"^(?:FAIL|ERROR): {test} .*?(?=^={{5,}}|^-{{5,}}\nRan |\Z)", ausgabe,
                        re.MULTILINE | re.DOTALL)
    return treffer.group(0) if treffer else ""


def zielstatus(ergebnis):
    """bestanden, verfehlt oder nicht_beobachtbar (Vorbedingung gescheitert, Abnahme lief
    nicht durch oder lieferte kein Ergebnis für die Zielprüfung)."""
    status = ergebnis["status"].get(ZIEL)
    if status == "ok":
        return "bestanden"
    if status is None or "Vorbedingung:" in _block(ergebnis["ausgabe"], ZIEL):
        return "nicht_beobachtbar"
    return "verfehlt"


def tests(name):
    """Alle Prüfungen der Aufgabe, geordnet nach Rolle."""
    klasse = {"A": "GruppeA", "B": "GruppeB", "GA": "GegenfallA", "GB": "GegenfallB"}[aufgaben.gruppe(name)]
    quelle = (PRUEFUNG / "abnahme.py").read_text(encoding="utf-8")
    abschnitt = quelle.split(f"class {klasse}(Basis):", 1)[1].split("\nclass ", 1)[0]
    namen = re.findall(r"def (test_\w+)\(", abschnitt)
    return {"ziel": ZIEL, "diagnose": [t for t in namen if t.startswith("test_diag_")],
            "uebrige": [t for t in namen if t != ZIEL and not t.startswith("test_diag_")]}


def vorlauf_laeufe(plan):
    namen = [*aufgaben.KANDIDATEN["A"], *aufgaben.KANDIDATEN["B"]]
    laeufe = [{"aufgabe": n, "bedingung": b, "seed": s}
              for n in namen for b in ("O", "D") for s in plan["stufen"]["vorlauf"]["seeds"]]
    laeufe += [{"aufgabe": n, "bedingung": "O", "seed": s}
               for n in aufgaben.GEGENFAELLE.values() for s in plan["stufen"]["vorlauf"]["seeds"]]
    return laeufe


def zeitplan(stufe, plan, eingeschlossen=None):
    """Vollständig durch reihenfolge_seed festgelegt. Haupt- und Gegenfall: Paare (Aufgabe,
    Seed) zufällig, je Paar die Bedingungen zufällig. Haupt braucht die eingeschlossenen
    Aufgaben aus dem Vorlauf."""
    zufall = random.Random(f"{plan['reihenfolge_seed']}-{stufe}")
    if stufe == "vorlauf":
        laeufe = vorlauf_laeufe(plan)
        zufall.shuffle(laeufe)
    else:
        namen = eingeschlossen if stufe == "haupt" else list(aufgaben.GEGENFAELLE.values())
        if not namen:
            raise ValueError("Hauptlauf braucht eingeschlossene Aufgaben")
        angaben = plan["stufen"][stufe]
        paare = [(n, s) for n in namen for s in angaben["seeds"]]
        zufall.shuffle(paare)
        laeufe = []
        for name, seed in paare:
            bedingungen = list(angaben["bedingungen"])
            zufall.shuffle(bedingungen)
            laeufe += [{"aufgabe": name, "bedingung": b, "seed": seed} for b in bedingungen]
    for nummer, lauf in enumerate(laeufe, 1):
        lauf["nr"] = nummer
    return laeufe
