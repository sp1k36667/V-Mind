"""Aufgaben der Aufgabensuche für Transfer v3: je Aufgabe eine Spezifikation und ein Gerüst
ohne Lösungslogik. Jede Aufgabe hat genau eine Falle, die `test_ziel_mechanismus` prüft.
Die Reihenfolge in REIHENFOLGE ist die vorab festgelegte Priorität bei Gleichstand."""

REIHENFOLGE = ["datumsimport", "kalender", "warteliste", "paketstatus", "bestellimport", "lager"]

# Name -> (Symbol in app.py, deutscher Titel)
AUFGABEN = {
    "datumsimport": ("parse_date", "Datumsimport"),
    "kalender": ("Calendar", "Raumkalender"),
    "warteliste": ("Waitlist", "Kursanmeldung mit Warteliste"),
    "paketstatus": ("Package", "Paketverfolgung"),
    "bestellimport": ("Importer", "Bestellimport"),
    "lager": ("Stock", "Lagerbestand"),
}

ALLGEMEIN = """Allgemeine Anforderungen: Nur Python-Standardbibliothek, eine Datei app.py, die das
vorgegebene Gerüst vollständig umsetzt (Klassen-, Funktions- und Methodennamen sowie Parameter
nicht ändern). Keine Kommandozeile nötig."""

SPEZIFIKATIONEN = {
    "datumsimport": """Datumsimport. Funktion `parse_date(text)` liest ein Datum und gibt ein
`datetime.date` zurück. Gültig ist ausschließlich das Format JJJJ-MM-TT: vierstelliges Jahr,
zweistelliger Monat und zweistelliger Tag, jeweils mit führender Null, getrennt durch
Bindestriche, ohne Leerzeichen davor oder danach. Alles andere löst ValueError aus, auch ein
Datum ohne führende Nullen wie "2026-1-5", ein Kalendertag, den es nicht gibt, wie
"2026-02-30", und Werte, die kein Text sind.""",
    "kalender": """Raumkalender für einen Tag. Klasse `Calendar()`. Zeiten sind Minuten seit
Mitternacht, ganze Zahlen von 0 bis 1440. Eine Reservierung von `start_min` bis `end_min`
umfasst den Beginn einschließlich und das Ende ausschließlich; es muss start_min < end_min
gelten. Ungültige Zeiten lösen ValueError aus. Eine Reservierung, die sich mit einer
bestehenden überschneidet, wird nicht gespeichert, und `reserve` liefert False. Direkt
aneinandergrenzende Reservierungen (Ende der einen gleich Beginn der anderen) überschneiden
sich nicht und sind erlaubt.""",
    "warteliste": """Kursanmeldung mit Warteliste. Klasse `Waitlist(capacity)`; `capacity` ist eine
ganze Zahl ab 1, sonst ValueError. Jede Buchung erhält eine neue ID (ganze Zahl ab 1). Die
ersten `capacity` aktiven Buchungen sind bestätigt, alle weiteren warten in
Buchungsreihenfolge. Wird eine bestätigte Buchung storniert, rückt die erste wartende
Buchung nach. Wird eine wartende Buchung storniert, wird sie aus der Warteliste entfernt.
Das Stornieren einer unbekannten oder bereits stornierten ID löst ValueError aus und ändert
nichts. Leere oder nur aus Leerzeichen bestehende Namen lösen ValueError aus.""",
    "paketstatus": """Paketverfolgung. Klasse `Package()`. Die Status in ihrer festen Reihenfolge:
"created", "in_transit", "out_for_delivery", "delivered". Ein neues Paket hat den Status
"created". `apply(event)` verarbeitet ein Ereignis, das einen dieser Status nennt. Ereignisse
können verspätet eintreffen: Ein Ereignis, das in der Reihenfolge nicht hinter dem aktuellen
Status liegt, wird ignoriert, der Status bleibt. Ein Ereignis darf Stufen überspringen.
Unbekannte Ereignisse und Werte, die kein Text sind, lösen ValueError aus; der Status bleibt
dann unverändert.""",
    "bestellimport": """Bestellimport. Klasse `Importer(path)` speichert dauerhaft als JSON-Datei an
genau dem übergebenen Pfad; die Datei existiert anfangs nicht, jede Änderung wird sofort
gespeichert. `ingest(event_id, cents)` verarbeitet eine Zahlung: `event_id` ist ein nicht
leerer Text, `cents` eine ganze Zahl größer 0; ungültige Werte lösen ValueError aus. Eine
Zahlung wird nur gezählt, wenn ihre `event_id` noch nie verarbeitet wurde, auch nicht von
einer früheren Instanz mit demselben Pfad; dann liefert `ingest` True. Andernfalls liefert
es False, und die Summe bleibt unverändert.""",
    "lager": """Lagerbestand eines Artikels. Klasse `Stock(initial)`; `initial` ist eine ganze Zahl
ab 0. Mengen für `deposit` und `withdraw` sind ganze Zahlen ab 1. Ungültige Werte lösen
ValueError aus. Eine Entnahme, die größer ist als der aktuelle Bestand, löst ValueError aus;
der Bestand bleibt dann unverändert. Der Bestand ist nie negativ.""",
}

GERUESTE = {
    "datumsimport": '''import datetime


def parse_date(text):
    """Liefert das Datum aus `text` (JJJJ-MM-TT) als datetime.date."""
    raise NotImplementedError
''',
    "kalender": '''class Calendar:
    """Reservierungen eines Raums an einem Tag."""

    def __init__(self):
        raise NotImplementedError

    def reserve(self, start_min, end_min):
        """Reserviert den Zeitraum; True bei Erfolg, False bei Überschneidung."""
        raise NotImplementedError

    def bookings(self):
        """Liefert alle Reservierungen nach Beginn sortiert: [(start_min, end_min), ...]."""
        raise NotImplementedError
''',
    "warteliste": '''class Waitlist:
    """Kurs mit begrenzten Plätzen und Warteliste."""

    def __init__(self, capacity):
        raise NotImplementedError

    def book(self, name):
        """Legt eine Buchung an und gibt ihre neue ID (int) zurück."""
        raise NotImplementedError

    def cancel(self, booking_id):
        """Storniert die Buchung mit der ID `booking_id`."""
        raise NotImplementedError

    def confirmed(self):
        """Liefert die Namen der bestätigten Buchungen in Buchungsreihenfolge."""
        raise NotImplementedError

    def waiting(self):
        """Liefert die Namen der wartenden Buchungen in Buchungsreihenfolge."""
        raise NotImplementedError
''',
    "paketstatus": '''class Package:
    """Status eines Pakets aus eintreffenden Ereignissen."""

    def __init__(self):
        raise NotImplementedError

    def apply(self, event):
        """Verarbeitet ein Ereignis."""
        raise NotImplementedError

    def status(self):
        """Liefert den aktuellen Status (str)."""
        raise NotImplementedError
''',
    "bestellimport": '''class Importer:
    """Zählt Zahlungen, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        raise NotImplementedError

    def ingest(self, event_id, cents):
        """Verarbeitet eine Zahlung; True, wenn sie gezählt wurde, sonst False."""
        raise NotImplementedError

    def total(self):
        """Liefert die Summe aller gezählten Zahlungen in Cent (int)."""
        raise NotImplementedError
''',
    "lager": '''class Stock:
    """Bestand eines Artikels."""

    def __init__(self, initial):
        raise NotImplementedError

    def deposit(self, quantity):
        """Erhöht den Bestand um `quantity`."""
        raise NotImplementedError

    def withdraw(self, quantity):
        """Verringert den Bestand um `quantity`."""
        raise NotImplementedError

    def balance(self):
        """Liefert den aktuellen Bestand (int)."""
        raise NotImplementedError
''',
}


def symbol(name):
    return AUFGABEN[name][0]


def spezifikation(name):
    return ALLGEMEIN + "\n\n" + SPEZIFIKATIONEN[name]


def geruest(name):
    return GERUESTE[name]
