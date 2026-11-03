#!/usr/bin/env python3
"""Simulierte Trennschärfe des Erfolgskriteriums für 40 gepaarte Läufe (L gegen O).

Annahme: Jedes Paar hat eine gemeinsame Schwierigkeit; O und L sind über eine
Gauß-Copula mit Korrelation rho verbunden. rho ist unbekannt und wird variiert.
Geprüft wird nur der Teil L gegen O: einseitiger exakter McNemar p < 0,05 UND
beobachteter Abstand mindestens 30 Prozentpunkte. P und die Aufgabenregel (3 von 4)
senken die Trennschärfe weiter; die Paare sind über die vier Aufgaben geclustert, das
Modell hier nimmt unabhängige Paare an und ist daher eher zu optimistisch.
"""

import random
from math import sqrt
from statistics import NormalDist

from auswerten import ALPHA, MIN_L_UEBER_O_PP, mcnemar_einseitig

PAARE = 40
LAEUFE = 20000


def staerke(p_o, p_l, rho, zufall):
    norm = NormalDist()
    grenze_o, grenze_l = norm.inv_cdf(p_o), norm.inv_cdf(p_l)
    treffer_test = treffer_kriterium = 0
    for _ in range(LAEUFE):
        b = c = summe_o = summe_l = 0
        for _ in range(PAARE):
            z1 = zufall.gauss(0, 1)
            z2 = rho * z1 + sqrt(1 - rho * rho) * zufall.gauss(0, 1)
            o, l = z1 < grenze_o, z2 < grenze_l
            summe_o += o
            summe_l += l
            b += l and not o
            c += o and not l
        signifikant = mcnemar_einseitig(b, c) < ALPHA
        treffer_test += signifikant
        treffer_kriterium += signifikant and 100 * (summe_l - summe_o) / PAARE >= MIN_L_UEBER_O_PP
    return treffer_test / LAEUFE, treffer_kriterium / LAEUFE


def main():
    zufall = random.Random(20261102)
    print(f"{PAARE} Paare, {LAEUFE} Simulationen je Zelle; Werte: nur McNemar / McNemar und >= 30 pp")
    print("| Basis O | wahres L | rho 0 | rho 0,3 | rho 0,6 |")
    print("|---:|---:|---:|---:|---:|")
    for p_o, p_l in ((0.5, 0.8), (0.5, 0.9), (0.4, 0.7), (0.3, 0.6), (0.5, 0.5)):
        zellen = []
        for rho in (0.0, 0.3, 0.6):
            test, kriterium = staerke(p_o, p_l, rho, zufall)
            zellen.append(f"{test:.2f} / {kriterium:.2f}")
        print(f"| {p_o:.0%} | {p_l:.0%} | " + " | ".join(zellen) + " |")


if __name__ == "__main__":
    main()
