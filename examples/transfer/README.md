# Transfer-Pilot: hilft eine geprüfte Erfahrung bei einer neuen Aufgabe?

Plan, Kriterien und offene Entscheidungen:
[docs/experiments/transfer-pilot-plan.md](../../docs/experiments/transfer-pilot-plan.md).
**Noch nicht eingefroren; keine gezählten Läufe.**

| Datei | Inhalt |
|---|---|
| `bedingungen.json` | Modell und Digest, Optionen, Erfahrung (L), Placebo (P), Seeds je Stufe |
| `aufgaben/*/spec.md` | Aufgabenbeschreibung für das Modell |
| `aufgaben/*/abnahme.py`, `aufgaben/gemeinsam.py` | Zielprüfung und übrige Prüfungen |
| `referenz/` | korrekte Lösungen, **nur** für Selbsttest und Attrappe, nie im Modellkontext |
| `selbsttest.py` | Referenzen bestehen; Zielprüfung trennt den Fehlertyp; Mutationen werden erkannt |
| `run.py` | Testhost; `--attrappe` prüft den Ablauf ohne Modell |
| `auswerten.py` | Kriterien je Stufe als JSON |
| `test_auswerten.py` | Auswertung, Zeitplan und Prompts mit erfundenen Daten |
| `trennschaerfe_gepaart.py` | simulierte Trennschärfe des gepaarten Kriteriums |

Prüfungen ohne Modell (je einzeln):

```sh
python3 examples/transfer/selbsttest.py
```

```sh
python3 examples/transfer/test_auswerten.py
```

```sh
python3 examples/transfer/run.py --stufe haupt --ausgabe /tmp/transfer-attrappe --attrappe
```

Gezählte Läufe nur nach Freigabe und am eingefrorenen Commit, je Stufe einzeln:

```sh
python3 examples/transfer/run.py --stufe vorlauf --ausgabe ../v-mind-transfer/vorlauf
```

```sh
python3 examples/transfer/auswerten.py ../v-mind-transfer/vorlauf
```

Haupt- und Gegenfall starten nur mit gültigem, bestandenem Vorlauf desselben Commits:

```sh
python3 examples/transfer/run.py --stufe haupt --vorlauf ../v-mind-transfer/vorlauf --ausgabe ../v-mind-transfer/haupt
```

```sh
python3 examples/transfer/auswerten.py ../v-mind-transfer/vorlauf ../v-mind-transfer/haupt ../v-mind-transfer/gegenfall
```

Generierter Code läuft ohne Sandbox mit den Rechten des Nutzers (Zeit- und
Ausgabelimits, `HOME` im Laufordner); nur auf einem eigenen Rechner ausführen. Rohdaten
gehören nicht ins Repository.
