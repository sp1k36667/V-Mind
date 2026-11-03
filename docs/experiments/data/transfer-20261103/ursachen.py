#!/usr/bin/env python3
"""NACHTRÄGLICHE Ursachenanalyse des Transfer-Pilots (nicht vorab geplant).

Ordnet jedem Fehlschlag der Zielprüfung die erste Fehlerzeile seines Prüfblocks zu und
fasst sie zu Klassen zusammen. Zusätzlich: Läufe, in denen die Zielprüfung den
gemessenen Fehlertyp überhaupt beobachten konnte (die Methode `list` existierte; sonst
bricht die Prüfung vor dem ID-Vergleich ab). Achtung: Die Bedingung kann beeinflussen, ob
`list` existiert; Raten über die beobachtbaren Läufe sind daher kein fairer Vergleich,
nur eine Beschreibung.

Aufruf: python3 ursachen.py (im Ordner dieser Datei).
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ORDNER = Path(__file__).resolve().parent
KLASSEN = [
    ("fehlende Methode list", r"has no attribute 'list'"),
    ("IDs nach Neuladen keine int", r"IDs nach Neuladen keine int"),
    ("ID nach Neuladen nicht gefunden", r"ValueError: .*(not found|nicht gefunden|Unknown ID|Unbekannte ID)"),
    ("Umwandlung auf falschem Typ (isdigit)", r"has no attribute 'isdigit'"),
    ("Vergleich str/int", r"not supported between instances of 'str' and 'int'"),
    ("Datei als beschädigt abgelehnt", r"ValueError: .*(Corrupt|Damaged|beschädigt)"),
    ("Syntaxfehler", r"SyntaxError"),
]


def erste_fehlerzeile(abnahme, ziel):
    block = re.search(rf"^(?:FAIL|ERROR): {ziel} .*?(?=^={{5,}}|^-{{5,}}\nRan |\Z)", abnahme,
                      re.MULTILINE | re.DOTALL)
    if not block:
        # Ohne Prüfblock (etwa Importfehler) steht die Ursache in der Gesamtausgabe.
        treffer = re.search(r"^\w*Error.*$", abnahme, re.MULTILINE)
        return treffer.group(0) if treffer else "ohne Fehlerzeile"
    zeilen = [z for z in block.group(0).splitlines() if re.match(r"^\w*(Error|Exception)\b", z)]
    return zeilen[0] if zeilen else "ohne Fehlerzeile"


def klasse(zeile):
    for name, muster in KLASSEN:
        if re.search(muster, zeile):
            return name
    return "andere"


def main():
    bericht = {}
    for stufe in ("vorlauf", "haupt", "gegenfall"):
        zaehler = defaultdict(Counter)
        beobachtbar = defaultdict(lambda: [0, 0])
        for lauf in sorted((ORDNER / stufe).iterdir()):
            if not lauf.is_dir():
                continue
            e = json.loads((lauf / "ergebnis.json").read_text(encoding="utf-8"))
            ziel = next(t for t in e["status"] if t.startswith("test_ziel_"))
            b = e["bedingung"]
            if e["ziel_bestanden"]:
                zaehler[b]["bestanden"] += 1
                beobachtbar[b][0] += 1
                beobachtbar[b][1] += 1
                continue
            k = klasse(erste_fehlerzeile((lauf / "abnahme.txt").read_text(encoding="utf-8"), ziel))
            zaehler[b][k] += 1
            if k != "fehlende Methode list":
                beobachtbar[b][1] += 1
        bericht[stufe] = {b: {"klassen": dict(zaehler[b].most_common()),
                              "list_vorhanden_bestanden": beobachtbar[b][0],
                              "list_vorhanden_laeufe": beobachtbar[b][1]}
                          for b in sorted(zaehler)}
    print(json.dumps(bericht, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
