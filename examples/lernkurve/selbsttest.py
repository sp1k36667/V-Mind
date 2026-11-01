#!/usr/bin/env python3
"""Prüft die Abnahmen selbst: Referenzlösungen müssen alles bestehen, gezielt kaputte
Varianten müssen genau den passenden Fallstrick verfehlen. Ohne Modell."""

import shutil
import sys
import tempfile
from pathlib import Path

from werkzeuge import REFERENZ, abnahme_ausfuehren, abnahme_einrichten, alle_tests, aufgaben

# Mutation der Referenzbasis -> Prüfung, die dann fehlschlagen muss.
MUTATIONEN = {
    "test_kaputtes_json_bleibt_erhalten": (
        'raise ValueError(f"Beschädigte Datei: {self.path}") from fehler',
        "self.items = []",
    ),
    "test_ids_steigen_nach_loeschen": (
        "neu = self.next_id",
        'neu = max([e["id"] for e in self.items], default=0) + 1',
    ),
    "test_unbekannte_id_valueerror": (
        'raise ValueError(f"Unbekannte ID: {id}")',
        "raise KeyError(id)",
    ),
    "test_leere_eingabe_valueerror": (
        "if not isinstance(wert, str) or not wert.strip():",
        "if not isinstance(wert, str):",
    ),
    "test_cli_fehler_exitcode": ("        return 1", "        return 0"),
    "test_persistenz_nach_wiederoeffnen": (
        "os.replace(tmp, self.path)",
        "os.replace(tmp, self.path.with_name('woanders.json'))",
    ),
}


def einrichten(aufgabe, ordner, ersetzung=None):
    basis = (REFERENZ / "basis.py").read_text()
    if ersetzung:
        alt, neu = ersetzung
        if alt not in basis:
            raise SystemExit(f"Mutation passt nicht mehr zur Referenz: {alt}")
        basis = basis.replace(alt, neu)
    (ordner / "basis.py").write_text(basis)
    shutil.copy(REFERENZ / f"{aufgabe}.py", ordner / "app.py")
    abnahme_einrichten(aufgabe, ordner)


def main():
    fehler = []
    for aufgabe in aufgaben():
        erwartet = alle_tests(aufgabe)
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp)
            einrichten(aufgabe, ordner)
            ergebnis = abnahme_ausfuehren(ordner)
            bestanden = sorted(t for t, s in ergebnis["status"].items() if s == "ok")
            if bestanden != erwartet or ergebnis["exit_code"] != 0:
                fehler.append(f"{aufgabe}: Referenz besteht nicht alles\n{ergebnis['ausgabe']}")
            print(f"{aufgabe}: Referenz {len(bestanden)}/{len(erwartet)}")
        for test, ersetzung in MUTATIONEN.items():
            with tempfile.TemporaryDirectory() as tmp:
                ordner = Path(tmp)
                einrichten(aufgabe, ordner, ersetzung)
                status = abnahme_ausfuehren(ordner, test)["status"]
                if status.get(test) == "ok":
                    fehler.append(f"{aufgabe}: Mutation für {test} wurde nicht erkannt")
        print(f"{aufgabe}: {len(MUTATIONEN)} Mutationen geprüft")
    if fehler:
        print("\n".join(fehler), file=sys.stderr)
        return 1
    print("Selbsttest bestanden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
