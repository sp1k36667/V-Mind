"""Gemeinsame Hilfen für Testhost, Selbsttest und Auswertung des Transfer-Pilots."""

import os
import re
import shutil
import subprocess
import sys
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


def _begrenzt_lesen(pfad):
    with open(pfad, "rb") as datei:
        inhalt = datei.read(MAX_AUSGABE_BYTES + 1)
    text = inhalt[:MAX_AUSGABE_BYTES].decode("utf-8", errors="replace")
    if len(inhalt) > MAX_AUSGABE_BYTES:
        text += f"\n[Ausgabe nach {MAX_AUSGABE_BYTES} Bytes abgeschnitten]"
    return text


def abnahme_ausfuehren(ziel, test=None):
    """Führt die Abnahme in ZIEL ohne Shell aus, mit Zeitlimit und begrenzter Ausgabe.

    Modellcode läuft mit den Rechten des Nutzers; HOME zeigt auf den Arbeitsordner,
    damit der Code nicht versehentlich ins echte Profil schreibt (keine Sandbox)."""
    ziel = Path(ziel)
    befehl = [sys.executable, "verification/abnahme.py"]
    if test:
        befehl.append(f"Abnahme.{test}")
    umgebung = {"PATH": os.environ.get("PATH", ""), "HOME": str(ziel), "LANG": "C.UTF-8",
                "PYTHONDONTWRITEBYTECODE": "1"}
    protokoll = ziel / "abnahme.log"
    with open(protokoll, "wb") as ausgabe:
        prozess = subprocess.Popen(befehl, cwd=ziel, stdout=ausgabe, stderr=subprocess.STDOUT,
                                   env=umgebung, start_new_session=True)
        try:
            exit_code = prozess.wait(timeout=ABNAHME_ZEITLIMIT)
        except subprocess.TimeoutExpired:
            os.killpg(prozess.pid, 9)
            prozess.wait()
            exit_code = 124
    text = _begrenzt_lesen(protokoll)
    protokoll.unlink()
    if exit_code == 124:
        text += f"\n[Zeitlimit von {ABNAHME_ZEITLIMIT} s überschritten]"
    status = {name: ergebnis for name, ergebnis in ERGEBNIS.findall(text)}
    return {"exit_code": exit_code, "status": status, "ausgabe": text}


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
