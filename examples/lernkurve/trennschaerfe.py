"""Exakter einseitiger Fisher-Test und simulierte Trennschärfe für den 12B-Transferpilot."""
import random
from math import comb


def fisher_einseitig(a, n1, b, n2):
    """P(X >= a) für Erfolge in Gruppe 1 bei festen Rändern (hypergeometrisch)."""
    k = a + b
    n = n1 + n2
    return sum(comb(n1, x) * comb(n2, k - x) for x in range(a, min(n1, k) + 1)) / comb(n, k)


def staerke(p0, p1, n, alpha=0.05, laeufe=20000):
    rng = random.Random(1)
    treffer = 0
    for _ in range(laeufe):
        b = sum(rng.random() < p0 for _ in range(n))
        a = sum(rng.random() < p1 for _ in range(n))
        treffer += fisher_einseitig(a, n, b, n) < alpha
    return treffer / laeufe


print("Beispiele n=20 je Gruppe, einseitig:")
for a, b in [(12, 6), (14, 6), (16, 8), (18, 10)]:
    print(f"  {a}/20 vs {b}/20: p = {fisher_einseitig(a, 20, b, 20):.3f}")
print("Trennschärfe bei Basis 50 %:")
for n in (20, 30, 40):
    for d in (0.3, 0.4):
        print(f"  n={n}, +{d:.0%}: {staerke(0.5, 0.5 + d, n):.2f}")
print("Trennschärfe bei Basis 40 %:")
for n in (20, 30, 40):
    for d in (0.3, 0.4):
        print(f"  n={n}, +{d:.0%}: {staerke(0.4, 0.4 + d, n):.2f}")
