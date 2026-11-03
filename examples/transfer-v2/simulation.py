#!/usr/bin/env python3
"""Simulierte Trennschärfe der gesamten Erfolgsregel von Transfer v2 (ohne Modell).

Plan: docs/experiments/transfer-v2-plan.md. Ohne Argument: BEDINGTE Trennschärfe nur des
Hauptvergleichs passend gegen unpassend (Regeln 1-4) bei fest eingeschlossenen Aufgaben,
ohne Vorlaufauswahl und ohne Schadensgrenzen. Mit `--vollstaendig`: gesamte Regel mit
Vorlaufauswahl (G1-G4), Hauptvergleich und Schadensgrenzen in Null-, Effekt- und
Schadensszenarien sowie die Begründung der Gegenfallgrenze.
Der gepoolte McNemar-Test ist nur bei austauschbaren Paaren exakt; bei aufgabenabhängigen
Effekten ist er eine Näherung.

Modell der Daten je Simulation:
- Jede Aufgabe t hat eine Rate unter unpassender Erfahrung m_t ~ N(M, SD_M), gekappt.
- Ihr wahrer Effekt d_t ~ N(D, SD_D); passende Rate a_t = m_t + d_t, gekappt.
- Je Seed ein Paar (passend, unpassend), über eine Gauß-Copula mit Korrelation RHO.

Erfolgsregel (wie im Plan, alle Teile zugleich):
1. gepoolter Abstand passend − unpassend >= MIN_ABSTAND_PP,
2. einseitiger McNemar über alle Paare p < ALPHA,
3. in jeder Gruppe passend > unpassend (Summe),
4. je Gruppe höchstens eine Aufgabe mit passend < unpassend.
"""

import random
import sys
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
          f"rho={rho}. Werte: nur McNemar / Regeln 1-4 (bedingt)")
    print("| Aufgaben je Gruppe | Seeds je Aufgabe | wahrer Effekt D | SD des Effekts | Trennschärfe |")
    print("|---:|---:|---:|---:|---:|")
    zellen = [(4, n, d, sd) for n in (10, 15, 20) for d in (0.0, 0.2, 0.3, 0.4) for sd in (0.0, 0.15)]
    zellen += [(3, 15, d, 0.15) for d in (0.0, 0.3, 0.4)]
    for aufgaben, seeds, d, sd_d in zellen:
        t, g = staerke(zufall, aufgaben, seeds, m, sd_m, d, sd_d, rho)
        print(f"| {aufgaben} | {seeds} | {d:.0%} | {sd_d:.0%} | {t:.2f} / {g:.2f} |")


if __name__ == "__main__" and len(sys.argv) == 1:
    main()


# ---------------------------------------------------------------------------
# Vollständige Regel: Vorlaufauswahl (G1-G4), Hauptvergleich, Schadensgrenzen.

VORLAUF_SEEDS = 8
G1_MIN, G2_MAX, G3_MIN, G4_MIN = 6, 4, 0.80, 6
UEBRIGE_JE_LAUF = 5
MAX_SCHADEN_PP = 10


def binom(zufall, n, p):
    return sum(zufall.random() < p for _ in range(n))


def szenario(zufall, s):
    """Eine vollständige Durchführung; liefert (Gesamterfolg, Grund des Scheiterns)."""
    eingeschlossen = []
    for gruppe in range(2):
        aufgaben = []
        for _ in range(s["aufgaben"]):
            o_t = kappen(zufall.gauss(s["o"], 0.15))
            d_t = kappen(zufall.gauss(s["d_rate"], 0.10))
            q_t = kappen(zufall.gauss(0.90, 0.05))
            # Technische Ausfälle: für G1/G3 nicht bestanden, für G2 konservativ wie bestanden.
            tech = s["technisch"]
            d_ok = sum(zufall.random() >= tech and zufall.random() < d_t for _ in range(VORLAUF_SEEDS))
            g2_zaehler = uebrige_ok = gueltig = 0
            for _ in range(VORLAUF_SEEDS):
                if zufall.random() < tech:
                    g2_zaehler += 1
                else:
                    gueltig += 1
                    g2_zaehler += zufall.random() < o_t
                    uebrige_ok += binom(zufall, UEBRIGE_JE_LAUF, q_t)
            g1 = d_ok >= G1_MIN
            g2 = g2_zaehler <= G2_MAX
            # G3 über die technisch gültigen Läufe (Anteil); ohne gültigen Lauf nicht erfüllt.
            g3 = gueltig > 0 and uebrige_ok >= G3_MIN * gueltig * UEBRIGE_JE_LAUF
            if g1 and g2 and g3:
                m_t = kappen(o_t + s["unspezifisch"])
                a_t = kappen(m_t + zufall.gauss(s["effekt"], s["sd_effekt"]))
                aufgaben.append((o_t, m_t, a_t, q_t))
        aufgaben = aufgaben[:s["max_aufgaben"]]  # erste eingeschlossene in fester Reihenfolge
        if len(aufgaben) < s["min_aufgaben"]:
            return False, "Gruppe nicht auswertbar"
        eingeschlossen.append(aufgaben)
    for _ in range(2):
        if binom(zufall, VORLAUF_SEEDS, s["gegenfall_o"] * (1 - s["technisch"])) < G4_MIN:
            return False, "Gegenfall nicht prüfbar"
    b = c = passend = unpassend = laeufe = 0
    uebrige_o = uebrige_p = uebrige_n = 0
    gruppen_summen = []
    for aufgaben in eingeschlossen:
        summen = []
        for o_t, m_t, a_t, q_t in aufgaben:
            # Technische Ausfälle im Hauptlauf zählen als nicht bestanden.
            g_m = NORM.inv_cdf(kappen(m_t * (1 - s["technisch"])))
            g_a = NORM.inv_cdf(kappen(a_t * (1 - s["technisch"])))
            sa = sm = 0
            for _ in range(s["seeds"]):
                z1 = zufall.gauss(0, 1)
                z2 = s["rho"] * z1 + sqrt(1 - s["rho"] ** 2) * zufall.gauss(0, 1)
                pa, pm = z1 < g_a, z2 < g_m
                sa += pa
                sm += pm
                b += pa and not pm
                c += pm and not pa
                uebrige_o += binom(zufall, UEBRIGE_JE_LAUF, q_t)
                uebrige_p += binom(zufall, UEBRIGE_JE_LAUF, kappen(q_t - s["schaden_uebrige"]))
                uebrige_n += UEBRIGE_JE_LAUF
            summen.append((sa, sm))
            passend += sa
            unpassend += sm
            laeufe += s["seeds"]
        gruppen_summen.append(summen)
    haupt = (100 * (passend - unpassend) / laeufe >= MIN_ABSTAND_PP
             and mcnemar_einseitig(b, c) < ALPHA
             and all(sum(a for a, _ in g) > sum(m for _, m in g) for g in gruppen_summen)
             and all(sum(a < m for a, m in g) <= 1 for g in gruppen_summen))
    if not haupt:
        return False, "Hauptkriterium verfehlt"
    if 100 * (uebrige_o - uebrige_p) / uebrige_n > MAX_SCHADEN_PP:
        return False, "Schaden übrige Prüfungen"
    for _ in range(2):
        fehl_o = s["gegenfall_seeds"] - binom(zufall, s["gegenfall_seeds"], s["gegenfall_o"])
        fehl_l = s["gegenfall_seeds"] - binom(zufall, s["gegenfall_seeds"],
                                              kappen(s["gegenfall_o"] - s["schaden_gegenfall"]))
        if fehl_l - fehl_o > s["gegenfall_grenze"]:
            return False, "Schaden Gegenfall"
    return True, "bestanden"


GRUND = {"aufgaben": 6, "max_aufgaben": 4, "min_aufgaben": 3, "o": 0.30, "d_rate": 0.85, "unspezifisch": 0.10, "effekt": 0.0, "sd_effekt": 0.15,
         "rho": 0.3, "seeds": 15, "gegenfall_o": 0.90, "gegenfall_seeds": 20,
         "gegenfall_grenze": 3, "schaden_uebrige": 0.0, "schaden_gegenfall": 0.0,
         "technisch": 0.03}

SZENARIEN = [
    ("Null: kein Effekt, kein unspezifischer Effekt", {"unspezifisch": 0.0, "sd_effekt": 0.0}),
    ("Null: nur unspezifischer Effekt +10 pp", {}),
    ("Null: Effekt je Aufgabe N(0, 15 pp)", {}),
    ("Effekt 30 pp, kein Schaden", {"effekt": 0.30}),
    ("Effekt 30 pp, keine technischen Ausfälle", {"effekt": 0.30, "technisch": 0.0}),
    ("Effekt 40 pp, kein Schaden", {"effekt": 0.40}),
    ("Effekt 30 pp, Grundrate O 50 %", {"effekt": 0.30, "o": 0.50}),
    ("Effekt 30 pp, Positivkontrolle nur 75 %", {"effekt": 0.30, "d_rate": 0.75}),
    ("Effekt 30 pp, Schaden übrige 15 pp", {"effekt": 0.30, "schaden_uebrige": 0.15}),
    ("Effekt 30 pp, Schaden Gegenfall 30 pp", {"effekt": 0.30, "schaden_gegenfall": 0.30}),
    ("Effekt 30 pp, Schaden Gegenfall 20 pp", {"effekt": 0.30, "schaden_gegenfall": 0.20}),
    ("Effekt 30 pp, nur 4 Kandidaten je Gruppe", {"effekt": 0.30, "aufgaben": 4}),
    ("Effekt 30 pp, 8 % technische Ausfälle", {"effekt": 0.30, "technisch": 0.08}),
    ("Null, 8 % technische Ausfälle", {"technisch": 0.08}),
]


def vollstaendig(simulationen=2000):
    zufall = random.Random(20261104)
    print(f"\nVollständige Regel, {simulationen} Durchführungen je Szenario; Vorlauf "
          f"{VORLAUF_SEEDS} Seeds (G1 >= {G1_MIN}, G2 <= {G2_MAX}, G3 >= {G3_MIN:.0%}, "
          f"G4 >= {G4_MIN}), Hauptlauf {GRUND['seeds']} Seeds, Gegenfall "
          f"{GRUND['gegenfall_seeds']} Seeds mit Grenze +{GRUND['gegenfall_grenze']}; "
          f"{GRUND['aufgaben']} Kandidaten je Gruppe, die ersten {GRUND['max_aufgaben']} "
          f"eingeschlossenen zählen, mindestens {GRUND['min_aufgaben']} nötig; technische "
          f"Ausfälle {GRUND['technisch']:.0%} je Lauf (G2 konservativ)")
    print("| Szenario | Gesamterfolg | häufigster Grund sonst |")
    print("|---|---:|---|")
    for name, abweichung in SZENARIEN:
        s = {**GRUND, **abweichung}
        gruende = {}
        erfolge = 0
        for _ in range(simulationen):
            ok, grund = szenario(zufall, s)
            erfolge += ok
            if not ok:
                gruende[grund] = gruende.get(grund, 0) + 1
        haeufig = max(gruende, key=gruende.get) if gruende else "–"
        print(f"| {name} | {erfolge / simulationen:.2f} | {haeufig} |")


def gegenfall_grenzen():
    """Wahrscheinlichkeit, die Gegenfallgrenze zu verletzen (ein Gegenfall)."""
    zufall = random.Random(5)
    print("\nGegenfall: P(Grenze verletzt) bei Grundrate O 90 %, 20000 Simulationen")
    print("| Seeds | Grenze | ohne Schaden | Schaden 20 pp | Schaden 30 pp |")
    print("|---:|---:|---:|---:|---:|")
    for seeds, grenze in ((10, 1), (10, 2), (15, 2), (15, 3), (20, 3), (20, 4)):
        werte = []
        for schaden in (0.0, 0.2, 0.3):
            verletzt = 0
            for _ in range(20000):
                fo = seeds - binom(zufall, seeds, 0.9)
                fl = seeds - binom(zufall, seeds, 0.9 - schaden)
                verletzt += fl - fo > grenze
            werte.append(verletzt / 20000)
        print(f"| {seeds} | +{grenze} | " + " | ".join(f"{w:.2f}" for w in werte) + " |")


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "--vollstaendig":
    gegenfall_grenzen()
    vollstaendig()
