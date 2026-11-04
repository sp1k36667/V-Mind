#!/usr/bin/env python3
"""Baut den R1-Wissensbestand K als neue Test-DB aus wissen/eintraege.json auf.

Aufruf: r1_wissen.py ZIEL_DB [VMIND]
Die DB darf noch nicht existieren. Einträge werden in fester Reihenfolge angelegt und mit dem
gespeicherten Nachweis validiert; die IDs müssen denen in eintraege.json und prompttexte.json
entsprechen. Echte vmind.db wird nie berührt.
"""

import json
import subprocess
import sys
from pathlib import Path

BASIS = Path(__file__).resolve().parent


def vmind(programm, *argumente):
    return subprocess.run([programm, *argumente], capture_output=True, text=True, check=True).stdout


def aufbauen(ziel, programm="vmind"):
    ziel = Path(ziel)
    if ziel.exists():
        raise SystemExit(f"{ziel} existiert schon; R1-Wissensbestand nur in eine neue Datei.")
    eintraege = json.loads((BASIS / "wissen" / "eintraege.json").read_text(encoding="utf-8"))
    vmind(programm, "init", str(ziel))
    for e in eintraege:
        bereich = [] if e["scope"] == "global" else ["--scope", e["scope"]]
        neu = json.loads(vmind(programm, "--json", *bereich, "add", str(ziel), e["kind"], e["problem"],
                               e["solution"], e["source"]))
        if neu["id"] != e["id"]:
            raise SystemExit(f"ID {neu['id']} statt {e['id']}; Aufbau abgebrochen.")
        vmind(programm, "validate", str(ziel), str(e["id"]), "claude-lehrer", e["evidence"])
    return len(eintraege)


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    print(f"{aufbauen(*sys.argv[1:])} Einträge angelegt und validiert.")
