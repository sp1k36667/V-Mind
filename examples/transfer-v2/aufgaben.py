"""Aufgaben von Transfer v2: eine Tabelle, aus der Spezifikation, Gerüst und Prüfung abgeleitet
werden. Gruppe A: Einträge unter int-ID-Schlüsseln, nur Textparameter (Falle A). Gruppe B:
Liste, ganze Zahlen > 0 ohne Wahrheitswerte (Falle B). GA/GB: Gegenfälle.
Die Reihenfolge in KANDIDATEN ist die vorab festgelegte Auswahlreihenfolge."""

KANDIDATEN = {
    "A": ["zitate", "geschenkideen", "vokabeln", "filmliste", "rezeptideen", "reiseziele"],
    "B": ["trainingslog", "punktestand", "pflanzen", "budget", "lesezeit", "wasserzaehler"],
}
GEGENFAELLE = {"GA": "postleitzahlen", "GB": "gewohnheiten"}

AUFGABEN = {
    # Gruppe A: Klasse, Textfeld 1, Textfeld 2 (änderbar), deutscher Titel
    "zitate": ("A", "Quotes", "text", "author", "Zitatsammlung"),
    "geschenkideen": ("A", "GiftIdeas", "idea", "person", "Geschenkideen"),
    "vokabeln": ("A", "Vocabulary", "word", "translation", "Vokabelheft"),
    "filmliste": ("A", "FilmList", "title", "director", "Filmliste"),
    "rezeptideen": ("A", "RecipeIdeas", "name", "cuisine", "Rezeptideen"),
    "reiseziele": ("A", "Destinations", "place", "country", "Reiseziele"),
    # Gruppe B: Klasse, Textfeld, Zahlfeld, deutscher Titel
    "trainingslog": ("B", "TrainingLog", "exercise", "minutes", "Trainingsprotokoll"),
    "punktestand": ("B", "Scoreboard", "player", "points", "Punktestand"),
    "pflanzen": ("B", "PlantCare", "plant", "interval_days", "Gießplan"),
    "budget": ("B", "Budget", "category", "cents", "Haushaltsbuch"),
    "lesezeit": ("B", "ReadingLog", "book", "minutes", "Lesezeiten"),
    "wasserzaehler": ("B", "WaterMeter", "room", "liters", "Wasserverbrauch"),
    # Gegenfälle
    "postleitzahlen": ("GA", "Postcodes", "code", "city", "Postleitzahlenverzeichnis"),
    "gewohnheiten": ("GB", "Habits", "name", "active", "Gewohnheiten"),
}

ALLGEMEIN = """Allgemeine Anforderungen: Nur Python-Standardbibliothek, eine Datei app.py, die das
vorgegebene Gerüst vollständig umsetzt (Klassen- und Methodennamen nicht ändern). Die Klasse
speichert dauerhaft als JSON-Datei an genau dem übergebenen Pfad; die Datei existiert
anfangs nicht. Jede Änderung wird sofort gespeichert. Leere oder nur aus Leerzeichen
bestehende Texte und ungültige Werte lösen ValueError aus. Eine vorhandene beschädigte
JSON-Datei löst ValueError aus und darf nicht verändert werden. Keine Kommandozeile nötig."""


def gruppe(name):
    return AUFGABEN[name][0]


def alle():
    return [*KANDIDATEN["A"], *KANDIDATEN["B"], *GEGENFAELLE.values()]


def spezifikation(name):
    g, klasse, f1, f2, titel = AUFGABEN[name]
    if g == "A":
        teil = f"""{titel}. Klasse `{klasse}(path)`.
Speicherformat: ein JSON-Objekt {{"next_id": <nächste freie ID>, "items": {{...}}}}; in "items"
steht jeder Eintrag unter seiner ID als Schlüssel, der Wert ist ein Objekt mit "{f1}" und "{f2}".
IDs sind ganze Zahlen (int) ab 1 und werden nie wiederverwendet, auch nach Löschen und
erneutem Öffnen nicht. Unbekannte IDs lösen ValueError aus."""
    elif g == "B":
        teil = f"""{titel}. Klasse `{klasse}(path)`.
Speicherformat: ein JSON-Objekt {{"items": [...]}}; jeder Eintrag ist ein Objekt mit "{f1}" und
"{f2}", in der Reihenfolge des Anlegens. "{f2}" ist eine ganze Zahl größer 0. Wahrheitswerte
(True, False) sind keine gültigen Zahlen und lösen ValueError aus, ebenso 0, negative Zahlen
und Kommazahlen. Ein unbekannter Index löst ValueError aus."""
    elif g == "GA":
        teil = f"""{titel}. Klasse `{klasse}(path)`.
Speicherformat: ein JSON-Objekt {{"items": {{...}}}}; in "items" steht der Ort unter der
Postleitzahl als Schlüssel. Postleitzahlen sind Texte aus genau fünf Ziffern; führende
Nullen gehören dazu (zum Beispiel "01067"). Eine unbekannte Postleitzahl löst ValueError aus."""
    else:
        teil = f"""{titel}. Klasse `{klasse}(path)`.
Speicherformat: ein JSON-Objekt {{"items": [...]}}; jeder Eintrag ist ein Objekt mit "{f1}" und
"{f2}", in der Reihenfolge des Anlegens. "{f2}" ist ein Wahrheitswert (True oder False);
andere Werte lösen ValueError aus. Ein unbekannter Index löst ValueError aus."""
    return ALLGEMEIN + "\n\n" + teil


def geruest(name):
    g, klasse, f1, f2, titel = AUFGABEN[name]
    kopf = f'''class {klasse}:
    """{titel}, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        raise NotImplementedError
'''
    if g == "A":
        methoden = f'''
    def add(self, {f1}, {f2}):
        """Legt einen Eintrag an und gibt seine neue ID (int) zurück."""
        raise NotImplementedError

    def list(self):
        """Liefert alle Einträge nach ID sortiert: [{{"id": int, "{f1}": str, "{f2}": str}}, ...]."""
        raise NotImplementedError

    def set_{f2}(self, id, {f2}):
        """Ändert "{f2}" des Eintrags mit der ID `id`."""
        raise NotImplementedError

    def remove(self, id):
        """Löscht den Eintrag mit der ID `id`."""
        raise NotImplementedError
'''
    elif g == "B":
        methoden = f'''
    def add(self, {f1}, {f2}):
        """Hängt einen Eintrag an."""
        raise NotImplementedError

    def list(self):
        """Liefert alle Einträge in Anlegereihenfolge: [{{"{f1}": str, "{f2}": int}}, ...]."""
        raise NotImplementedError

    def total(self):
        """Liefert die Summe aller "{f2}" (int)."""
        raise NotImplementedError

    def remove(self, index):
        """Löscht den Eintrag an Position `index` (ab 0)."""
        raise NotImplementedError
'''
    elif g == "GA":
        methoden = '''
    def add(self, code, city):
        """Legt die Postleitzahl `code` (Text) mit dem Ort `city` an oder überschreibt sie."""
        raise NotImplementedError

    def city(self, code):
        """Liefert den Ort zur Postleitzahl `code`."""
        raise NotImplementedError

    def list(self):
        """Liefert alle Einträge nach Postleitzahl sortiert: [{"code": str, "city": str}, ...]."""
        raise NotImplementedError

    def remove(self, code):
        """Löscht die Postleitzahl `code`."""
        raise NotImplementedError
'''
    else:
        methoden = '''
    def add(self, name, active):
        """Hängt eine Gewohnheit an; `active` ist True oder False."""
        raise NotImplementedError

    def list(self):
        """Liefert alle Einträge in Anlegereihenfolge: [{"name": str, "active": bool}, ...]."""
        raise NotImplementedError

    def set_active(self, index, active):
        """Setzt `active` des Eintrags an Position `index` (ab 0)."""
        raise NotImplementedError

    def remove(self, index):
        """Löscht den Eintrag an Position `index` (ab 0)."""
        raise NotImplementedError
'''
    return kopf + methoden
