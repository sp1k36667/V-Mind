# R1: Reparatur mit validierten Lehrerhinweisen (Gemma 4 12B)

Plan: [docs/experiments/r1-plan.md](../../docs/experiments/r1-plan.md). Pilot mit 36 Fällen,
Arme O/P/L, höchstens 108 Generierungen. **Noch nicht eingefroren; keine Modellläufe.**

| Datei | Inhalt |
|---|---|
| `bedingungen.json` | Modell, Fallquelle, Familienregel, Seeds, Abruf- und Prompt-Grenzen, Kriterien |
| `wissen/eintraege.json` | 2 Lehrereinträge (Bereich `r1`) und 9 fachfremde Einträge mit Nachweis |
| `wissen/prompttexte.json` | ausgespielte Texte (`wann`, `richtig`), ohne falsches Codemuster |
| `wissen/belege/` | Lernfälle vorher/nachher mit Abnahme |
| `r1_werkzeuge.py` | Fallauswahl, Relevanzregel, P-Zuteilung, Prompt, Zeitplan |
| `r1_wissen.py` | baut den Wissensbestand als neue Test-DB |
| `r1_host.py` | Host; `--attrappe` ohne Modell |
| `r1_auswerten.py` | Auswertung als JSON |
| `test_r1.py`, `selbsttest.py` | Prüfungen ohne Modell |
| `r1_trennschaerfe.py` | Simulation der Kriterien |

Prüfungen ohne Modell (je einzeln, im Ordner `examples/r1`):

```sh
python3 test_r1.py
```

```sh
python3 selbsttest.py
```

Gezählter Lauf nur am eingefrorenen, sauberen Commit:

```sh
python3 r1_host.py --ausgabe ../../../v-mind-r1/lauf
```

```sh
python3 r1_auswerten.py ../../../v-mind-r1/lauf
```

Generierter Code läuft ohne Sandbox wie im Pilot; nur auf einem eigenen Rechner ausführen.
Rohdaten gehören nicht ins Repository.
