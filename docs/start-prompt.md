# Startanweisung und Host-Anbindung

`prompts/start.de.md` ist die gemeinsame Quelle für den KI-Startprompt.
`vmind start-prompt` gibt den vollständigen Text aus; mit `--json` erscheint er unter
`prompt`. Der lokale Ollama-Adapter bindet dieselbe Datei beim Kompilieren ein.

## Lokaler Ollama-Testclient

Der Adapter sendet die Anweisung im Feld `system`. Im Datenobjekt des Nutzerprompts
steht `vmind_runtime` mit `mode: context_only`, dem Bereich, der Gesprächs-ID,
`conversation_persistence: host_managed`, `tools_available: false` und
`terminal_available: false`. Dazu kommen `memory`, `project_context` und `question`.

Das lokale Modell kann mit dem bereitgestellten Kontext antworten, aber keine
Werkzeuge selbst aufrufen. `ask`/`chat` speichern den Gesprächsverlauf im Host.
Die Anweisung beschreibt vorhandene Produktfunktionen und grenzt sie von den
Funktionen ab, die dieses konkrete Modell tatsächlich ausführen kann.

## Externe KI mit Werkzeugen

1. Startprompt über die dafür vorgesehene Konfiguration des Hosts laden.
2. Reale V-Mind-Werkzeuge oder Terminalzugriff bereitstellen; nicht nur deren Namen nennen.
3. Tatsächlichen Datenbankpfad, stabilen Projektbereich und Gesprächs-ID konfigurieren.
4. Der KI die reale Betriebsart mitteilen, beispielsweise Werkzeugzugriff und ob
   der Host die Gesprächsspeicherung übernimmt.
5. `describe` und `resume` beim Start aufrufen; danach bei Bedarf `recall` und ältere
   Historie lesen. Laufende Arbeit über `log` dokumentieren.

Ein Host kann die JSONL-Schnittstelle über einen dauerhaften Unterprozess
`vmind serve DB` ansteuern. Das Zuordnen seiner Tool-Aufrufe zu diesem Prozess ist
weiterhin Aufgabe des Hosts. V-Mind stellt noch keinen MCP-Server bereit.

## Grenzen

Ein Startprompt allein garantiert weder Werkzeugaufrufe noch korrektes Verhalten
oder vollständige Berichte. Speicheroperationen müssen tatsächlich ausgeführt und
ihr Erfolg geprüft werden. Eine externe KI ohne Anbindung kann nicht automatisch
ihre Gespräche oder Arbeitsschritte in V-Mind ablegen.

Die Anweisung ist nicht vom Datenbestand abhängig. Das konkrete Projektwissen kommt
bei jedem Aufruf neu aus SQLite. Dadurch wird ein Projektwechsel nicht durch einen
fest in den Prompt geschriebenen Projektstand verhindert. Geänderte Befugnisse
muss der Host ausdrücklich und wahrheitsgemäß mitteilen.
