"""Gemeinsame Hilfen für Testhost, Selbsttest und Auswertung des Transfer-Pilots."""

import json
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import selectors
import time
from pathlib import Path

BASIS = Path(__file__).resolve().parent
AUFGABEN = BASIS / "aufgaben"
REFERENZ = BASIS / "referenz"
ID_AUFGABEN = ("ausgaben", "leihliste", "rezepte", "termine")
GEGENFALL = "vorrat"
ABNAHME_ZEITLIMIT = 90
MAX_AUSGABE_BYTES = 200_000
ERGEBNIS = re.compile(r"^(test_\w+) \(.*\) \.\.\. (ok|FAIL|ERROR)", re.MULTILINE)


def abnahme_einrichten(aufgabe, ziel):
    """Kopiert Abnahme und gemeinsame Prüfungen nach ZIEL/verification."""
    pruefung = Path(ziel) / "verification"
    pruefung.mkdir(parents=True, exist_ok=True)
    shutil.copy(AUFGABEN / aufgabe / "abnahme.py", pruefung / "abnahme.py")
    shutil.copy(AUFGABEN / "gemeinsam.py", pruefung / "gemeinsam.py")


def _prozessgruppe_beenden(prozess):
    try:
        os.killpg(prozess.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def abnahme_ausfuehren(ziel, test=None):
    """Führt die Abnahme in ZIEL ohne Shell aus. Zeitlimit und Ausgabelimit gelten während
    der Ausführung: Bei Überschreitung wird die ganze Prozessgruppe beendet.

    Modellcode läuft mit den Rechten des Nutzers; HOME zeigt auf den Arbeitsordner,
    damit der Code nicht versehentlich ins echte Profil schreibt (keine Sandbox).
    Ergebnis `abbruch`: None, "zeitlimit" oder "ausgabelimit"."""
    ziel = Path(ziel)
    befehl = [sys.executable, "verification/abnahme.py"]
    if test:
        befehl.append(f"Abnahme.{test}")
    umgebung = {"PATH": os.environ.get("PATH", ""), "HOME": str(ziel), "LANG": "C.UTF-8",
                "PYTHONDONTWRITEBYTECODE": "1"}
    prozess = subprocess.Popen(befehl, cwd=ziel, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, env=umgebung, start_new_session=True)
    gelesen = bytearray()
    abbruch = None
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
        # Auch nach Ende des Elternprozesses koennen Enkel dieselbe Pipe offenhalten.
        _prozessgruppe_beenden(prozess)
    exit_code = prozess.wait()
    prozess.stdout.close()
    text = bytes(gelesen).decode("utf-8", errors="replace")
    if abbruch == "zeitlimit":
        text += f"\n[Zeitlimit von {ABNAHME_ZEITLIMIT} s überschritten, Prozessgruppe beendet]"
    elif abbruch == "ausgabelimit":
        text += f"\n[Ausgabe über {MAX_AUSGABE_BYTES} Bytes, Prozessgruppe beendet]"
    status = {name: ergebnis for name, ergebnis in ERGEBNIS.findall(text)}
    return {"exit_code": exit_code, "status": status, "ausgabe": text, "abbruch": abbruch}


def format_fehler(ausgabe, test):
    """True, wenn die Zielprüfung an einer Formatvorgabe scheiterte. unittest hängt die
    eigene Meldung an („… : Format: …“), daher Suche in der AssertionError-Zeile."""
    block = re.search(rf"^(?:FAIL|ERROR): {test} .*?(?=^={{5,}}|^-{{5,}}\nRan |\Z)", ausgabe,
                      re.MULTILINE | re.DOTALL)
    return bool(block and re.search(r"^AssertionError: .*\bFormat:", block.group(0), re.MULTILINE))


def alle_tests(aufgabe):
    text = (AUFGABEN / aufgabe / "abnahme.py").read_text(encoding="utf-8")
    if aufgabe != GEGENFALL:
        text += (AUFGABEN / "gemeinsam.py").read_text(encoding="utf-8")
    return sorted(set(re.findall(r"def (test_\w+)\(", text)))


def zieltest(aufgabe):
    ziel = [t for t in alle_tests(aufgabe) if t.startswith("test_ziel_")]
    if len(ziel) != 1:
        raise RuntimeError(f"{aufgabe}: genau eine Zielprüfung erwartet, gefunden {ziel}")
    return ziel[0]


def uebrige_tests(aufgabe):
    return [t for t in alle_tests(aufgabe) if not t.startswith("test_ziel_")]


def plan_laden():
    return json.loads((BASIS / "bedingungen.json").read_text(encoding="utf-8"))


def zeitplan(stufe, plan):
    """Gepaarte Läufe (Aufgabe, Seed) in zufälliger Reihenfolge; je Paar die Bedingungen in
    zufälliger Reihenfolge. Vollständig durch reihenfolge_seed festgelegt."""
    angaben = plan["stufen"][stufe]
    zufall = random.Random(f"{plan['reihenfolge_seed']}-{stufe}")
    paare = [(a, s) for a in angaben["aufgaben"] for s in angaben["seeds"]]
    zufall.shuffle(paare)
    laeufe = []
    for aufgabe, seed in paare:
        bedingungen = list(angaben["bedingungen"])
        zufall.shuffle(bedingungen)
        laeufe.extend({"aufgabe": aufgabe, "seed": seed, "bedingung": b} for b in bedingungen)
    for nummer, lauf in enumerate(laeufe, 1):
        lauf["nr"] = nummer
    return laeufe
