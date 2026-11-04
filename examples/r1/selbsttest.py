#!/usr/bin/env python3
"""Selbsttest von R1 ohne Modell.

1. Belege der Lehrereinträge reproduzieren: Pilot-Abnahme auf wissen/belege vorher/nachher.
2. Wissensbestand aus eintraege.json aufbauen: 11 validierte Einträge mit festen IDs.
3. Relevanzregel auf allen Lernfällen: genau der Eintrag der eigenen Familie, kein fremder.
4. Vollständige Attrappe: 108 Aufrufe, gültige Auswertung; zweiter Start sendet nichts.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import r1_auswerten
import r1_host
import r1_wissen
import r1_werkzeuge as w

ERWARTET = {  # Lernfall -> (nicht ok vorher, nicht ok nachher)
    "005-ausgaben-O-s1002": ({"test_cli_fehler_exitcode", "test_ziel_ids_nach_neuladen"}, {"test_cli_fehler_exitcode"}),
    "015-leihliste-O-s1003": ({"test_doppelte_rueckgabe_valueerror", "test_texte_nach_neuladen",
                               "test_ziel_ids_nach_neuladen"}, set()),
}


def belege(fehler):
    for fall, (vorher, nachher) in ERWARTET.items():
        aufgabe = fall.split("-")[1]
        for stand, soll in (("vorher", vorher), ("nachher", nachher)):
            with tempfile.TemporaryDirectory() as tmp:
                ziel = Path(tmp)
                (ziel / "app.py").write_text((w.BASIS / "wissen" / "belege" / f"{fall}-{stand}" / "app.py")
                                             .read_text(encoding="utf-8"), encoding="utf-8")
                w.abnahme_einrichten(aufgabe, ziel)
                status = w.abnahme_ausfuehren(ziel)["status"]
            ist = {t for t in w.alle_tests(aufgabe) if status.get(t) != "ok"}
            if ist != soll:
                fehler.append(f"Beleg {fall}-{stand}: nicht ok {sorted(ist)} statt {sorted(soll)}")
        print(f"Beleg {fall}: geprüft", flush=True)


def wissen_und_abruf(fehler, db, plan):
    r1_wissen.aufbauen(db)
    stats = json.loads(subprocess.run(["vmind", "--json", "--scope", "r1", "stats", str(db)], capture_output=True,
                                      text=True, check=True).stdout)
    if stats["validated"] != 11 or stats["pending"] != 0:
        fehler.append(f"Wissensbestand: {stats}")
    for fall in w.kandidaten(plan, plan["lernaufgaben"]):
        text = (w.REPO / fall["ordner"] / "abnahme.txt").read_text(encoding="utf-8", errors="replace")
        ids = [t["id"] for t in w.abruf_jsonl(db, w.anfrage(text, plan), plan) if w.passend(t, text)]
        soll = [int(i) for i, fam in plan["lehrer_familien"].items() if fam == fall["familie"]]
        if ids[:3] != soll:
            fehler.append(f"Abruf Lernfall {fall['ordner']}: {ids} statt {soll}")
    print("Wissensbestand und Abruf auf Lernfällen: geprüft", flush=True)


def attrappe(fehler):
    with tempfile.TemporaryDirectory() as tmp:
        ziel = Path(tmp) / "lauf"
        befehl = [sys.executable, str(w.BASIS / "r1_host.py"), "--ausgabe", str(ziel), "--attrappe"]
        for _ in range(2):
            subprocess.run(befehl, capture_output=True, text=True, check=True, cwd=w.BASIS)
        if len(r1_host.protokoll_lesen(ziel)) != 108:
            fehler.append("Attrappe: nicht genau 108 Aufrufe nach zwei Starts")
        bericht = r1_auswerten.auswerten(*r1_auswerten.laden(ziel))
        if not bericht["gueltig"] or bericht["kennzahlen"]["O"]["repariert"] != 0:
            fehler.append(f"Attrappe: Auswertung {bericht['probleme']}")
    print("Attrappe: geprüft", flush=True)


def main():
    plan = w.plan_laden()
    fehler = []
    belege(fehler)
    with tempfile.TemporaryDirectory() as tmp:
        wissen_und_abruf(fehler, Path(tmp) / "wissen.db", plan)
    attrappe(fehler)
    if fehler:
        print("\n".join(fehler), file=sys.stderr)
        return 1
    print("Selbsttest bestanden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
