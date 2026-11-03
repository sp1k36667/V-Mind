#!/usr/bin/env python3
"""Simulierte Trennschärfe der gesamten Erfolgsregel von Transfer v2 (ohne Modell).

Plan: docs/experiments/transfer-v2-plan.md. Simuliert wird nur der Hauptvergleich
passende gegen unpassende Erfahrung über die eingeschlossenen Aufgaben zweier Gruppen
(A: Schlüsselfalle, B: bool-Falle). Schadensgrenzen werden nicht simuliert (sie können
das Ergebnis nur weiter verschlechtern).

Modell der Daten je Simulation:
- Jede Aufgabe t hat eine Rate unter unpassender Erfahrung m_t ~ N(M, SD_M), gekappt.
- Ihr wahrer Effekt d_t ~ N(D, SD_D); passende Rate a_t = m_t + d_t, gekappt.
- Je Seed ein Paar (passend, unpassend), über eine Gauß-Copula mit Korrelation RHO.

Erfolgsregel (wie im Plan, alle Teile zugleich):
1. gepoolter Abstand passend − unpassend >= MIN_ABSTAND_PP,
2. einseitiger exakter McNemar über alle Paare p < ALPHA,
3. in jeder Gruppe passend > unpassend (Summe),
4. je Gruppe höchstens eine Aufgabe mit passend < unpassend.
"""

import random
from math import comb, sqrt
from statistics import NormalDist

MIN_ABSTAND_PP = 20
ALPHA = 0.05
SIMULATIONEN = 4000
NORM = NormalDist()


def mcnemar_einseitig(b, c):
    n = b + c
    return 1.0 if n == 0 else sum(comb(n, k) for k in range(b, n + 1)) / 2 ** n


def kappen(p):
    return min(max(p, 0.01), 0.99)


def eine_simulation(zufall, aufgaben_je_gruppe, seeds, m, sd_m, d, sd_d, rho):
    gruppen = []
    b = c = treffer_passend = treffer_unpassend = laeufe = 0
    for _ in range(2):
        aufgaben = []
        for _ in range(aufgaben_je_gruppe):
            m_t = kappen(zufall.gauss(m, sd_m))
            a_t = kappen(m_t + zufall.gauss(d, sd_d))
            g_m, g_a = NORM.inv_cdf(m_t), NORM.inv_cdf(a_t)
            summe_a = summe_m = 0
            for _ in range(seeds):
                z1 = zufall.gauss(0, 1)
                z2 = rho * z1 + sqrt(1 - rho * rho) * zufall.gauss(0, 1)
                passend, unpassend = z1 < g_a, z2 < g_m
                summe_a += passend
                summe_m += unpassend
                b += passend and not unpassend
                c += unpassend and not passend
            aufgaben.append((summe_a, summe_m))
            treffer_passend += summe_a
            treffer_unpassend += summe_m
            laeufe += seeds
        gruppen.append(aufgaben)
    abstand_ok = 100 * (treffer_passend - treffer_unpassend) / laeufe >= MIN_ABSTAND_PP
    test_ok = mcnemar_einseitig(b, c) < ALPHA
    richtung_ok = all(sum(a for a, _ in g) > sum(u for _, u in g) for g in gruppen)
    aufgaben_ok = all(sum(a < u for a, u in g) <= 1 for g in gruppen)
    return test_ok, abstand_ok and test_ok and richtung_ok and aufgaben_ok


def staerke(zufall, aufgaben_je_gruppe, seeds, m, sd_m, d, sd_d, rho):
    nur_test = gesamt = 0
    for _ in range(SIMULATIONEN):
        t, g = eine_simulation(zufall, aufgaben_je_gruppe, seeds, m, sd_m, d, sd_d, rho)
        nur_test += t
        gesamt += g
    return nur_test / SIMULATIONEN, gesamt / SIMULATIONEN


def main():
    zufall = random.Random(20261103)
    m, sd_m, rho = 0.30, 0.15, 0.3
    print(f"{SIMULATIONEN} Simulationen je Zelle; unpassend M={m:.0%} (SD {sd_m:.0%} je Aufgabe), "
          f"rho={rho}. Werte: nur McNemar / gesamte Regel")
    print("| Aufgaben je Gruppe | Seeds je Aufgabe | wahrer Effekt D | SD des Effekts | Trennschärfe |")
    print("|---:|---:|---:|---:|---:|")
    zellen = [(4, n, d, sd) for n in (10, 15, 20) for d in (0.0, 0.2, 0.3, 0.4) for sd in (0.0, 0.15)]
    zellen += [(3, 15, d, 0.15) for d in (0.0, 0.3, 0.4)]
    for aufgaben, seeds, d, sd_d in zellen:
        t, g = staerke(zufall, aufgaben, seeds, m, sd_m, d, sd_d, rho)
        print(f"| {aufgaben} | {seeds} | {d:.0%} | {sd_d:.0%} | {t:.2f} / {g:.2f} |")


if __name__ == "__main__":
    main()
