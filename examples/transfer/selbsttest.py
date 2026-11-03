#!/usr/bin/env python3
"""Prüft die Abnahmen des Transfer-Pilots ohne Modell.

1. Jede Referenz besteht alle Prüfungen.
2. Referenz ohne Schlüsselumwandlung: Zielprüfung scheitert, alle übrigen bestehen.
   Damit misst die Zielprüfung genau den Fehlertyp und die übrigen sind unabhängig davon.
3. Gegenfall mit Umwandlung der Namensschlüssel: Zielprüfung scheitert.
4. Allgemeine Mutationen werden von der jeweils passenden übrigen Prüfung erkannt.
"""

import shutil
import sys
import tempfile
from pathlib import Path

from werkzeuge import (GEGENFALL, ID_AUFGABEN, REFERENZ, abnahme_ausfuehren,
                       abnahme_einrichten, alle_tests, uebrige_tests, zieltest)

OHNE_UMWANDLUNG = ("{int(k): dict(v)", "{k: dict(v)")
GEGENFALL_UMWANDLUNG = ("{str(k): zahl(v", "{int(k): zahl(v")
MUTATIONEN = {
    "test_kaputtes_json_bleibt_erhalten": (
        'raise ValueError(f"Beschädigte Datei: {pfad}") from fehler', "return standard"),
    "test_ids_steigen_in_einer_instanz": (
        "neu = self.next_id", "neu = max(self.items, default=0) + 1"),
    "test_unbekannte_id_valueerror": ('raise ValueError(f"Unbekannte ID: {id}")', "raise KeyError(id)"),
    "test_leere_eingabe_valueerror": (
        "if not isinstance(wert, str) or not wert.strip():", "if not isinstance(wert, str):"),
    "test_cli_fehler_exitcode": ("        return 1", "        return 0"),
    "test_texte_nach_neuladen": ("os.replace(tmp, pfad)", "os.replace(tmp, pfad.with_name('x.json'))"),
}


def ersetzen(text, ersetzung, datei):
    alt, neu = ersetzung
    if text.count(alt) != 1:
        raise SystemExit(f"Mutation passt nicht genau einmal in {datei}: {alt}")
    return text.replace(alt, neu)


def einrichten(aufgabe, ordner, basis_ersetzung=None, app_ersetzung=None):
    basis = (REFERENZ / "basis.py").read_text(encoding="utf-8")
    app = (REFERENZ / f"{aufgabe}.py").read_text(encoding="utf-8")
    if basis_ersetzung:
        basis = ersetzen(basis, basis_ersetzung, "basis.py")
    if app_ersetzung:
        app = ersetzen(app, app_ersetzung, f"{aufgabe}.py")
    (ordner / "basis.py").write_text(basis, encoding="utf-8")
    (ordner / "app.py").write_text(app, encoding="utf-8")
    abnahme_einrichten(aufgabe, ordner)


def pruefen(aufgabe, **ersetzungen):
    with tempfile.TemporaryDirectory() as tmp:
        ordner = Path(tmp)
        einrichten(aufgabe, ordner, **ersetzungen)
        return abnahme_ausfuehren(ordner)


def main():
    fehler = []
    for aufgabe in (*ID_AUFGABEN, GEGENFALL):
        erwartet = alle_tests(aufgabe)
        ergebnis = pruefen(aufgabe)
        bestanden = sorted(t for t, s in ergebnis["status"].items() if s == "ok")
        if bestanden != erwartet or ergebnis["exit_code"] != 0:
            fehler.append(f"{aufgabe}: Referenz besteht nicht alles\n{ergebnis['ausgabe']}")
        print(f"{aufgabe}: Referenz {len(bestanden)}/{len(erwartet)}")
    for aufgabe in ID_AUFGABEN:
        status = pruefen(aufgabe, basis_ersetzung=OHNE_UMWANDLUNG)["status"]
        if status.get(zieltest(aufgabe)) == "ok":
            fehler.append(f"{aufgabe}: Zielprüfung erkennt fehlende Umwandlung nicht")
        abhaengig = [t for t in uebrige_tests(aufgabe) if status.get(t) != "ok"]
        if abhaengig:
            fehler.append(f"{aufgabe}: übrige Prüfungen hängen vom Fehlertyp ab: {abhaengig}")
        for test, ersetzung in MUTATIONEN.items():
            if pruefen(aufgabe, basis_ersetzung=ersetzung)["status"].get(test) == "ok":
                fehler.append(f"{aufgabe}: Mutation für {test} nicht erkannt")
        print(f"{aufgabe}: Fehlertyp getrennt, {len(MUTATIONEN)} Mutationen geprüft")
    status = pruefen(GEGENFALL, app_ersetzung=GEGENFALL_UMWANDLUNG)["status"]
    if status.get(zieltest(GEGENFALL)) == "ok":
        fehler.append("vorrat: Zielprüfung erkennt Fehlanwendung der Umwandlung nicht")
    print("vorrat: Fehlanwendung der Umwandlung erkannt")
    if fehler:
        print("\n".join(fehler), file=sys.stderr)
        return 1
    print("Selbsttest bestanden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
