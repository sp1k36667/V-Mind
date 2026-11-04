# Aufgabensuche für Transfer v3 mit Gemma 4 12B

Plan und Regel: [docs/experiments/transfer-v3-suche-plan.md](../../docs/experiments/transfer-v3-suche-plan.md).
Reine Vorauswahl aus höchstens 15 Aufrufen, keine Wirksamkeitsaussage.
**Noch nicht eingefroren; keine Modellläufe.**

| Datei | Inhalt |
|---|---|
| `aufgaben.py` | 6 Aufgaben mit Spezifikation und Gerüst; Reihenfolge = Priorität |
| `bedingungen.json` | Modell und Digest, direkte Anweisungen, Regel, Seeds |
| `pruefung/abnahme.py` | Zielprüfung mit Status bestanden / verfehlt / nicht beobachtbar, Diagnose, übrige Prüfungen |
| `referenz.py` | korrekte Lösungen, Fallen und Mutationen, **nur** für Selbsttest und Attrappe |
| `selbsttest.py` | Referenzen bestehen; Falle ergibt „verfehlt“ ohne Einfluss auf übrige Prüfungen; Mutationen werden erkannt |
| `run.py` | Host für Stufe o (12 Läufe ohne Hilfe) und d (höchstens 3 mit direkter Hilfe); `--attrappe` ohne Modell |
| `auswerten.py` | Eignung, Rang, Auswahl und Bestätigung als JSON |
| `test_suche.py` | Regeln, Zeitplan, Prompts und Host-Schutz mit erfundenen Daten |

Prüfungen ohne Modell (je einzeln):

```sh
python3 examples/transfer-v3-suche/selbsttest.py
```

```sh
python3 examples/transfer-v3-suche/test_suche.py
```

Gezählte Läufe nur nach Freeze, beide Stufen in denselben Ausgabeordner:

```sh
python3 examples/transfer-v3-suche/run.py --stufe o --ausgabe ../v-mind-transfer-v3-suche
```

```sh
python3 examples/transfer-v3-suche/run.py --stufe d --ausgabe ../v-mind-transfer-v3-suche
```

```sh
python3 examples/transfer-v3-suche/auswerten.py ../v-mind-transfer-v3-suche/o ../v-mind-transfer-v3-suche/d
```

Generierter Code läuft ohne Sandbox mit den Rechten des Nutzers (Zeit- und
Ausgabelimits, `HOME` im Laufordner); nur auf einem eigenen Rechner ausführen. Rohdaten
gehören nicht ins Repository.
