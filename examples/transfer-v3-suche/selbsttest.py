#!/usr/bin/env python3
"""Prüft die Abnahmen der Aufgabensuche ohne Modell.

1. Jede Referenz besteht alle Prüfungen (Ziel, Diagnose, übrige).
2. Referenz mit genau der Falle: Zielstatus „verfehlt“ (nicht „nicht beobachtbar“), alle
   übrigen Prüfungen bestehen. Damit misst das Ziel die Falle, und die übrigen Prüfungen
   hängen nicht von ihr ab.
3. Umbenanntes Hauptsymbol und Syntaxfehler: Zielstatus „nicht beobachtbar“.
4. Jede Mutation wird von der erwarteten übrigen Prüfung erkannt.
"""

import sys
import tempfile
from pathlib import Path

import aufgaben
import referenz
from werkzeuge import abnahme_ausfuehren, abnahme_einrichten, tests, zielstatus


def pruefen(name, variante=None):
    with tempfile.TemporaryDirectory() as tmp:
        ordner = Path(tmp)
        (ordner / "app.py").write_text(referenz.quelltext(name, variante), encoding="utf-8")
        abnahme_einrichten(name, ordner)
        return abnahme_ausfuehren(ordner)


def main():
    fehler = []
    for name in aufgaben.REIHENFOLGE:
        rollen = tests(name)
        alle = [rollen["ziel"], *rollen["diagnose"], *rollen["uebrige"]]
        e = pruefen(name)
        offen = [t for t in alle if e["status"].get(t) != "ok"]
        if offen or e["exit_code"] != 0:
            fehler.append(f"{name}: Referenz besteht nicht: {offen}\n{e['ausgabe'][-1500:]}")
        e = pruefen(name, "falle")
        if zielstatus(e) != "verfehlt":
            fehler.append(f"{name}: Falle ergibt Zielstatus {zielstatus(e)}\n{e['ausgabe'][-1500:]}")
        abhaengig = [t for t in rollen["uebrige"] if e["status"].get(t) != "ok"]
        if abhaengig:
            fehler.append(f"{name}: übrige Prüfungen hängen von der Falle ab: {abhaengig}")
        for variante in ("umbenannt", "syntaxfehler"):
            status = zielstatus(pruefen(name, variante))
            if status != "nicht_beobachtbar":
                fehler.append(f"{name}: {variante} ergibt Zielstatus {status}")
        for mutation, (_, _, erwartet) in referenz.MUTATIONEN[name].items():
            status = pruefen(name, mutation)["status"]
            gescheitert = [t for t in rollen["uebrige"] if status.get(t) != "ok"]
            if erwartet not in gescheitert:
                fehler.append(f"{name}: Mutation {mutation} nicht von {erwartet} erkannt ({gescheitert})")
        print(f"{name}: geprüft ({len(rollen['uebrige'])} übrige, Diagnose {rollen['diagnose']})",
              flush=True)
    if fehler:
        print("\n".join(fehler), file=sys.stderr)
        return 1
    print("Selbsttest bestanden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
