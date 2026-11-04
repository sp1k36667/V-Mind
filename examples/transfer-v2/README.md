# Transfer v2: gekreuzte Erfahrungen mit Gemma 4 12B

Plan, Regeln und Simulation: [docs/experiments/transfer-v2-plan.md](../../docs/experiments/transfer-v2-plan.md).
**Noch nicht eingefroren; keine Modellläufe.**

| Datei | Inhalt |
|---|---|
| `aufgaben.py` | Tabelle der 12 Kandidaten und 2 Gegenfälle; erzeugt Spezifikation und Gerüst |
| `bedingungen.json` | Modell und Digest, Erfahrungen A/B, direkte Anweisung D, Gates, Kriterien, Seeds |
| `pruefung/abnahme.py` | Zielprüfung mit Status bestanden / verfehlt / nicht beobachtbar, Diagnose, übrige Prüfungen |
| `referenz.py` | korrekte Lösungen und gezielte Varianten, **nur** für Selbsttest und Attrappe |
| `selbsttest.py` | Referenzen bestehen; Falle ergibt „verfehlt“ ohne Einfluss auf übrige Prüfungen; umbenanntes `list()` und Syntaxfehler ergeben „nicht beobachtbar“; Mutationen werden erkannt |
| `run.py` | Testhost für Vorlauf, Haupt- und Gegenfall; `--attrappe` prüft den Ablauf ohne Modell |
| `auswerten.py` | Gates, Auswahl, Erfolgsregel, Schadensgrenzen und Gesamtergebnis als JSON |
| `test_v2.py` | Regeln, Zeitpläne, Prompts und Host-Schutz mit erfundenen Daten |
| `simulation.py` | bedingte Trennschärfe; mit `--vollstaendig` die gesamte Regel |

Prüfungen ohne Modell (je einzeln):

```sh
python3 examples/transfer-v2/selbsttest.py
```

```sh
python3 examples/transfer-v2/test_v2.py
```

```sh
python3 examples/transfer-v2/simulation.py --vollstaendig
```

Gezählte Läufe nur nach Freeze, je Stufe einzeln; Haupt- und Gegenfall nur mit einem
Vorlauf desselben Commits, der die Fortsetzung erlaubt:

```sh
python3 examples/transfer-v2/run.py --stufe vorlauf --ausgabe ../v-mind-transfer-v2/vorlauf
```

```sh
python3 examples/transfer-v2/run.py --stufe haupt --vorlauf ../v-mind-transfer-v2/vorlauf --ausgabe ../v-mind-transfer-v2/haupt
```

```sh
python3 examples/transfer-v2/run.py --stufe gegenfall --vorlauf ../v-mind-transfer-v2/vorlauf --ausgabe ../v-mind-transfer-v2/gegenfall
```

```sh
python3 examples/transfer-v2/auswerten.py ../v-mind-transfer-v2/vorlauf ../v-mind-transfer-v2/haupt ../v-mind-transfer-v2/gegenfall
```

Generierter Code läuft ohne Sandbox mit den Rechten des Nutzers (Zeit- und
Ausgabelimits, `HOME` im Laufordner); nur auf einem eigenen Rechner ausführen. Rohdaten
gehören nicht ins Repository.
