"""Gemeinsame Hilfen für Testhost und Selbsttest der Lernkurve."""

import re
import shutil
import subprocess
import sys
from pathlib import Path

BASIS = Path(__file__).resolve().parent
AUFGABEN = BASIS / "aufgaben"
REFERENZ = BASIS / "referenz"
ABNAHME_ZEITLIMIT = 90
ERGEBNIS = re.compile(r"^(test_\w+) \(.*\) \.\.\. (ok|FAIL|ERROR)", re.MULTILINE)


def aufgaben():
    return sorted(p.name for p in AUFGABEN.iterdir() if (p / "abnahme.py").exists())


def abnahme_einrichten(aufgabe, ziel):
    """Kopiert Abnahme und gemeinsame Prüfungen nach ZIEL/verification."""
    pruefung = Path(ziel) / "verification"
    pruefung.mkdir(parents=True, exist_ok=True)
    shutil.copy(AUFGABEN / aufgabe / "abnahme.py", pruefung / "abnahme.py")
    shutil.copy(AUFGABEN / "gemeinsam.py", pruefung / "gemeinsam.py")
    return pruefung / "abnahme.py"


def abnahme_ausfuehren(ziel, test=None):
    """Führt die Abnahme in ZIEL aus; liefert Status je Prüfung und die Ausgabe."""
    befehl = [sys.executable, "verification/abnahme.py"]
    if test:
        befehl.append(f"Abnahme.{test}")
    try:
        lauf = subprocess.run(
            befehl, cwd=ziel, capture_output=True, text=True, timeout=ABNAHME_ZEITLIMIT
        )
        ausgabe = lauf.stderr + lauf.stdout
        exit_code = lauf.returncode
    except subprocess.TimeoutExpired:
        ausgabe, exit_code = f"Zeitlimit von {ABNAHME_ZEITLIMIT} s überschritten", 124
    status = {name: ergebnis for name, ergebnis in ERGEBNIS.findall(ausgabe)}
    return {"exit_code": exit_code, "status": status, "ausgabe": ausgabe}


def alle_tests(aufgabe):
    """Namen aller Prüfungen einer Aufgabe, ermittelt an der Referenzlösung."""
    text = (AUFGABEN / "gemeinsam.py").read_text() + (AUFGABEN / aufgabe / "abnahme.py").read_text()
    return sorted(set(re.findall(r"def (test_\w+)\(", text)))
