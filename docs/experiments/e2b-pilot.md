# Lokaler E2B-Pilotversuch, 31. Oktober 2026

## Fragestellung

Kann ein kleineres Modell eine bekannte Programmieraufgabe zuverlässiger bearbeiten,
wenn ein externer Speicher passende geprüfte Lösungen eines stärkeren Modells liefert?
Der Versuch untersucht Wiederverwendung bekannten Wissens, nicht das Lernen neuer
Modellgewichte oder die Übertragung auf unbekannte Aufgaben.

## Aufgabe und Vorgeschichte

Ein deutscher Aufgabenplaner in Python sollte mit Standardbibliotheken Aufgaben in
JSON speichern und hinzufügen, auflisten, erledigen und entfernen. Geprüft wurden
Persistenz nach Wiederöffnung, stabile IDs nach Löschung, Fehler bei leeren Texten
und unbekannten IDs sowie unveränderte beschädigte Dateien und echte CLI-Aufrufe.

Ein erster E2B-Entwurf scheiterte mehrfach. Mit konkretem Testfeedback und Führung
durch den Host erzeugte das vorhandene Gemma-4-12B-Modell eine korrekte `app.py`
und `test_app.py`. Zehn Modelltests und sieben davon getrennt durch Codex erstellte
Abnahmeprüfungen bestanden. Diese beiden vollständigen Referenzdateien wurden mit
Prüfnachweis in V-Mind abgelegt. Die Freigabe erfolgte durch den Testleiter; eine
vollständig automatische Wissensvalidierung durch die nutzende KI ist noch offen.

## Neustartvergleich

Der alte Projektstand wurde archiviert. Der aktive Ordner enthielt keine alten
Programmdateien mehr; die SQLite-Wissensdatenbank blieb erhalten. Beide Bedingungen
bekamen frische Gespräche und dieselbe Aufgabenbeschreibung, denselben Startprompt,
dieselben Ausgabeanweisungen und dieselben Prüfungen.

- Modell: `vmind-gemma4:e2b`, Gemma 4 E2B, Q4_K_M, lokal über Ollama 0.40.13.
- Hardware: AMD Radeon RX 6700 XT, bestehende ROCm-Umgebung.
- Kontext: 8.192 Tokens. Ausgabelimit: 2.400 Tokens. Temperatur: 0. Seed: 42.
- Höchstens zwei Versuche pro Bedingung. Fehler wurden aus tatsächlichen Testläufen
  zurückgegeben; während dieser beiden Läufe gab es keine manuellen Codekorrekturen.
- Ohne Wissen: keine gespeicherten Lösungen im Modellkontext.
- Mit Wissen: echter SQLite-FTS5-Abruf der passenden validierten Referenzdatei; der
  vollständige gespeicherte Quelltext samt Herkunft wurde im Modellkontext geliefert.
- Dateien wurden in beiden Bedingungen aus neuen E2B-Antworten geschrieben. Eine
  direkte Host-Kopieroperation aus dem Referenzspeicher gab es in diesem Vergleich nicht.

Der Host bestimmte die Arbeitsschritte. Gemessen wird deshalb Codeausgabe mit und
ohne bereitgestelltes Wissen, keine selbstständige Werkzeugplanung durch E2B.

## Ergebnisse pro Versuch

| Bedingung | Versuch | Unabhängige Abnahme | Eigene Modelltests |
|---|---:|---:|---:|
| Ohne V-Mind-Wissen | 1 | 2/7 | 3/10 |
| Ohne V-Mind-Wissen | 2 | 2/7 | keine reguläre Suite ausgeführt |
| Mit V-Mind-Wissen | 1 | 7/7 | keine reguläre Suite ausgeführt |
| Mit V-Mind-Wissen | 2 | 7/7 | 10/10 |

Eine nicht ausgeführte Suite zählt nicht als bestanden. Import-/Syntaxfehler der
Modelltests verhinderten in den entsprechenden Fällen einen regulären Lauf.
Die unabhängige Abnahme blieb für beide Bedingungen gleich und wurde nicht vom
Modell geändert. Ihre sieben Fälle prüfen:

1. Speicherung und Datensatzfelder nach Wiederöffnung.
2. Dauerhafte Änderungen durch Erledigen und Entfernen.
3. Keine Wiederverwendung gelöschter IDs.
4. Zurückweisung leerer bzw. reiner Whitespace-Eingaben.
5. Zurückweisung unbekannter IDs.
6. Beschädigte JSON-Dateien werden nicht überschrieben.
7. Echter CLI-Ablauf über getrennte Prozesse.

Die finale `app.py` und `test_app.py` mit Wissen sind bytegleich zur geprüften
12B-Referenz. E2B reproduzierte also den abgerufenen Quelltext erfolgreich. Eine
unabhängige Neuentwicklung oder Anpassung an eine neue Aufgabenvariante wurde damit
nicht gezeigt.

## Zeitmessung

Ausgewertet wurden die Dauerfelder der gespeicherten Ollama-Antworten für die
Erzeugung von `app.py` und `test_app.py`, jeweils über beide Versuche summiert.
Es sind keine gemessenen Gesamtzeiten des Projekts einschließlich Tests und Hostarbeit.

| Modellzeit in Sekunden | Ohne Wissen | Mit Wissen |
|---|---:|---:|
| Gesamtdauer der Modellaufrufe | 46,487 | 17,135 |
| Darin Modellladen | 2,817 | 0,003 |
| Kontextverarbeitung | 4,708 | 3,375 |
| Generierung | 38,783 | 13,575 |

Die Gesamtdauer enthält kleinen weiteren Verwaltungsaufwand, weshalb die Teilzeiten
nicht exakt zur Gesamtdauer aufsummieren. Insgesamt wurden ohne Wissen 6.720 und
mit Wissen 3.003 Ausgabe-Tokens erzeugt. Der Gesamtlauf mit Wissen war rund 2,7-mal
schneller bzw. benötigte rund 63 Prozent weniger Modellzeit. Nach Abzug des
Modellladens beträgt der Faktor rund 2,5. Ein Warm-/Cold-Cache-Effekt und die
Ausführungsreihenfolge wurden nicht durch Wiederholungen ausgeglichen.

## Grenzen und nächste Tests

Es handelt sich um ein Projekt mit maximal zwei Versuchen je Bedingung. Daraus
folgt keine statistisch belastbare Erfolgsquote. Der Vorteil trat bei vollständigen
bekannten Referenzlösungen auf. Geänderte Anforderungen, widersprüchliches Wissen,
nur kurze Erfahrungsnotizen, neue Aufgaben und wiederholte Messungen fehlen noch.

Die lokalen Datenbanken, vollständigen Gespräche und Rohprotokolle sind aus
Datenschutzgründen nicht Teil dieses Repositorys. Die experimentellen Hostskripte
unter `examples/` dokumentieren den Ablauf, benötigen aber vorbereitete lokale
Fixtures. Ein eigenständig lauffähiger öffentlicher Benchmark mit vollständig
veröffentlichten Aufgaben und Fixtures steht noch aus.

Die 28 Rust-Tests des V-Mind-Kerns prüfen die Speicher- und Schnittstellenfunktionen.
Sie sind kein Nachweis für die Qualität eines Sprachmodells und werden getrennt
vom hier beschriebenen Programmierexperiment ausgewiesen.
