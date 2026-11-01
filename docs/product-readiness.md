# Produktreife: lokales KI-Projektgedächtnis

Arbeitsziel nach Nutzerauftrag vom 1. November 2026. Version 0.2.0 ist ein geprüfter
Prototyp, keine abgeschlossene Produktreife. Dieses Dokument ist eine Abnahmeliste,
keine Behauptung, dass die offenen Punkte bereits umgesetzt sind.

## Für wen und wofür

Zunächst einzelne Entwickler und kleine, vertrauenswürdige Teams, die mit lokalen
CLI-/MCP-Clients an längeren Projekten arbeiten. Ein Rechner bzw. eine lokale,
zugriffsgeschützte Datenbank. Kein öffentlich erreichbarer Mehrmandantendienst.
Modellunabhängiges Projektgedächtnis, nachvollziehbare Erfahrungen und Wiederaufnahme
sind die zugesagten Funktionen; eine allgemeine Lernwirkung ist nicht zugesagt.

## Abnahme vor Empfehlung für den regelmäßigen Einsatz

- [ ] Installation aus einem Release auf einem frischen Benutzerprofil ohne Rust/SQLite-Werkzeuge praktisch geprüft; Fehler und Rückweg beschrieben.
- [ ] Einrichtung eines realen MCP-Clients aus vollständigem Beispiel geprüft; Diagnose benennt fehlende Voraussetzungen und verändert keine Datenbank.
- [ ] Vor jedem Upgrade einer vorhandenen Dateidatenbank automatisch eine geprüfte Sicherung; bei Sicherungsfehler kein Upgrade. Fehlgeschlagene Migration bleibt atomar.
- [ ] Konsistente explizite Sicherung ohne Überschreiben, Wiederherstellung einer Kopie praktisch geprüft; laufende Clients und alte Versionen berücksichtigt.
- [ ] Gleichzeitige Zugriffe durch mehrere Prozesse, Sperrkonflikte und Prozessabbruch geprüft. Keine pauschale WAL-Pflicht auf unbekannten Dateisystemen.
- [ ] Quellen, Pending-/Validiert-/Rückzugsstatus und Projektfilter bleiben nach Sicherung, Neustart und Upgrade korrekt.
- [ ] Abrufkorpus mit vorab definierten Treffern, Ablenkern und Nichttreffern; berichtete Treffergenauigkeit und bekannte Lücken.
- [ ] Kontrollierter Fortsetzungstest mit 12B und vorab eingefrorenen Fragen: richtige Antworten, erfundene Angaben, Zeit und Kontextumfang; Ergebnisse einschließlich Fehlschlägen veröffentlicht.
- [ ] Vergleiche trennen Neustart ohne Übergabe, manuelle Übergabe und V-Mind. Ein Vorteil gegenüber einer leeren Sitzung belegt keinen Vorteil gegenüber einer gleichwertigen manuellen Übergabe.
- [ ] Vertrauensgrenzen verständlich: MCP bietet kein validate; ein Client mit Shell-/Dateizugriff kann dennoch validieren oder SQLite verändern. Bereiche sind keine Zugriffskontrolle. Keine automatische Wahrheitsgarantie. *Stand: in README/README.de beschrieben (Abschnitt „Vertrauen, Datenschutz und Sicherung“); Gegenprüfung offen.*
- [ ] Datenschutz: gespeicherte Inhalte, Backups, Modellübertragung und Umgang mit versehentlich gespeicherten Geheimnissen beschrieben; Korrektur-/Löschweg praktisch geprüft.
- [ ] Datenportabilität und Wiederherstellung ohne Anbieterbindung dokumentiert; eine SQLite-Datei ist bereits portabel, ein geprüfter Export kann dies ergänzen.
- [ ] Gegenprüfung durch den jeweils anderen Teilnehmer und Release-/Upgradeprüfung am tatsächlich veröffentlichten Paket.

## Arbeitsweise

Nur ein Teilnehmer schreibt Code oder Versionen; Übergabe ausdrücklich im Teamkanal.
Der andere prüft unabhängig, trennt Beobachtungen von Berichten und bereitet Entwürfe
vor. Testerfolg ersetzt weder Nutzenmessung noch eine fachlich passende Prüfung einer
Erfahrung. Offene Kriterien bleiben offen, bis entsprechende Belege vorliegen.

## Erste Arbeitspakete

1. Datensicherheit: read-only `doctor`, geprüfte `backup`-Operation, automatische
   Sicherung vor Migration, reale Wiederherstellungs- und Fehlerfalltests.
2. Mehrprozessbetrieb und Vertrauensgrenzen; echte Einrichtung ohne Entwicklerumgebung.
3. Abruf- und Fortsetzungsnachweis; erst danach eine belastbare Aussage zum Nutzen.
4. Datenschutz/Korrektur, verbleibende Betriebsprobleme, unabhängige Gesamtabnahme.

Der GPU-Index bleibt eine spätere Optimierung, sofern Messungen ihn rechtfertigen.
Die funktionierende ROCm-Installation bleibt bestehen.
