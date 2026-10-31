# Experimentelle Gemma-Projekttests

`gemma_project_agent.py` lässt ein lokales Gemma-Modell einen kleinen Python-
Aufgabenplaner erzeugen. Der Host führt die festen Schritte und Dateischreibvorgänge
aus, reicht Fehler zurück und protokolliert sie in V-Mind. Es ist keine allgemeine
vollautonome Agentenimplementierung. Quelltext stammt vom Modell; Hoststeuerung und
unabhängige Abnahme stammen von Codex.

Auf dem Entwicklungs-PC wurden zunächst E2B und anschließend das vorhandene
`gemma-4-local:latest` (12B) getestet. E2B scheiterte bei der Neuentwicklung mehrfach.
Die finale Implementierung und korrekten Programmtests stammen von 12B.
`--model` wählt das Modell für einen neuen Lauf. `--resume` setzt das in `.vmind/host.json`
gespeicherte Modell und Gespräch fort. `--pause-after-write` beendet nach dem ersten
Schreiben, um eine Fortsetzung aus dem dauerhaften Speicher zu prüfen.

Der Zielordner muss existieren und beim neuen Lauf noch keine Testdateien enthalten.
Werkzeuge schreiben nur `app.py`, `test_app.py`, `README.md`. Der Host ruft festgelegte
unittest-Prüfungen auf. Diese Python-Prozesse sind nicht vom Betriebssystem isoliert.

`gemma_reuse_test.py` prüft einen anderen Fall: E2B wählt bereits validierte
Referenzdateien aus V-Mind aus; der Host schreibt exakt die ausgewählte solution.
Das ist bewusste Wiederverwendung, kein Nachweis einer selbstständigen Neuentwicklung.
Der Zielordner für diesen Test darf noch nicht existieren. Quelle und Ergebnis teilen
sich dieselbe V-Mind-Datenbank und verwenden getrennte Projektbereiche.

Die ursprünglichen Testprojekte, Gespräche und Rohprotokolle sind lokale Daten
und nicht Teil dieses Repositorys. `gemma_regeneration_test.py` erwartet einen
vorbereiteten Testordner mit `.vmind/restart-setup.json`, einer V-Mind-Datenbank
und einer unabhängigen Abnahmedatei. Die Skripte sind experimentelle Testhosts,
kein fertig eingerichteter Benchmark und kein allgemeiner KI-Agent.

Die Beispiele ergänzen keine automatische allgemeine Codex-/ChatGPT-Anbindung.
