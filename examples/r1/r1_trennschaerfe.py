"""Gepaarte Trennschärfe für R1 (Arme O/P/L), Monte Carlo. Alle Werte sind bedingt auf die
hier gesetzten Annahmen, keine zugesicherte Trennschärfe.

Je Fall: Grundwahrscheinlichkeit der Reparatur q ~ Beta(Mittel p_o, Konzentration 4).
Abruf je Fall: richtig (r), falsch aber nicht leer (w), leer (1 - r - w).
- O: Erfolg mit q.
- L: richtig -> q + u + d; falsch -> q + u; leer -> q (Gedächtnis leer).
- P: nur wenn L nicht leer ist, gleich langer fachfremder Text -> q + u; sonst leer -> q.
Regression (vorher bestandene Prüfung scheitert danach) je Arm mit g; unter L bei nicht leerem
Gedächtnis g + h.
Kriterien: (1) L - O >= 15 pp, (2) McNemar L gegen O einseitig exakt p < 0,05,
(3) L - P >= 10 pp, (4) Regressionsanteil L - O <= 10 pp. Erfolg = alle vier.
"""
import math
import random
import sys

N, LAEUFE = 36, 4000


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(b, n + 1)) / 2 ** n


def beta(rng, mittel, k=4):
    return rng.betavariate(max(mittel * k, 1e-3), max((1 - mittel) * k, 1e-3))


def lauf(rng, p_o, d, u, r, w, g, h):
    o = l = p = b = c = reg_o = reg_l = 0
    for _ in range(N):
        q = beta(rng, p_o)
        z = rng.random()
        abruf = "richtig" if z < r else ("falsch" if z < r + w else "leer")
        so = rng.random() < q
        sl = rng.random() < min(1.0, q + (u + d if abruf == "richtig" else u if abruf == "falsch" else 0))
        sp = rng.random() < min(1.0, q + (u if abruf != "leer" else 0))
        o, l, p = o + so, l + sl, p + sp
        b += sl and not so
        c += so and not sl
        reg_o += rng.random() < g
        reg_l += rng.random() < (g + h if abruf != "leer" else g)
    return ((l - o) / N >= 0.15 and mcnemar(b, c) < 0.05 and (l - p) / N >= 0.10
            and (reg_l - reg_o) / N <= 0.10)


def anteil(p_o=0.3, d=0.3, u=0.0, r=0.8, w=0.1, g=0.1, h=0.0, seed=1):
    rng = random.Random(seed)
    return sum(lauf(rng, p_o, d, u, r, w, g, h) for _ in range(LAEUFE)) / LAEUFE


SZENARIEN = [
    ("Null: kein Effekt", dict(d=0.0)),
    ("Null: nur unspezifisch +10 pp", dict(d=0.0, u=0.10)),
    ("Null: nur unspezifisch +20 pp", dict(d=0.0, u=0.20)),
    ("Effekt 20 pp", dict(d=0.20)),
    ("Effekt 30 pp", dict(d=0.30)),
    ("Effekt 40 pp", dict(d=0.40)),
    ("Effekt 30 pp, Abruf richtig 60 %, falsch 20 %", dict(r=0.6, w=0.2)),
    ("Effekt 30 pp, Abruf richtig 95 %, falsch 0 %", dict(r=0.95, w=0.0)),
    ("Effekt 30 pp, unspezifisch +10 pp", dict(u=0.10)),
    ("Effekt 30 pp, O-Grundrate 50 %", dict(p_o=0.5)),
    ("Effekt 30 pp, O-Grundrate 15 %", dict(p_o=0.15)),
    ("Effekt 30 pp, Schaden: Regression +15 pp", dict(h=0.15)),
    ("Effekt 30 pp, Schaden: Regression +25 pp", dict(h=0.25)),
]

if __name__ == "__main__":
    for n in [int(a) for a in sys.argv[1:]] or [36]:
        N = n
        print(f"N = {n} (Annahmen: O 30 %, Abruf richtig 80 %, falsch 10 %, Regression O 10 %, sofern nicht anders)")
        for name, werte in SZENARIEN:
            print(f"  {name:48s} {anteil(**werte):.2f}")
