import sys
import json
import os
import re

def validate_date(date_str):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise ValueError("Ungültiges Datumsformat. Erwartet: JJJJ-MM-TT")
    try:
        # Einfache Validierung ohne datetime Modul (da nur Standardlib, aber datetime ist Standard)
        from datetime import datetime
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Ungültiges Datum")

class Calendar:
    def __init__(self, path):
        self.path = path
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                if "next_id" not in data or "items" not in data:
                    raise ValueError("Beschädigte Datei")
                self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Beschädigte Datei")
        else:
            self.data = {"next_id": 1, "items": {}}
        self.save()

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, date):
        if not title or title.isspace():
            raise ValueError("Titel darf nicht leer sein")
        validate_date(date)
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"title": title, "date": date}
        self.data["next_id"] += 1
        self.save()
        return new_id

    def list_items(self):
        items = []
        for idx, val in self.data["items"].items():
            items.append({"id": int(idx), "title": val["title"], "date": val["date"]})
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, entry_id, date):
        if entry_id not in self.data["items"]:
            raise ValueError("ID nicht gefunden")
        validate_date(date)
        self.data["items"][entry_id]["date"] = date
        self.save()

    def remove(self, entry_id):
        if entry_id not in self.data["items"]:
            raise ValueError("ID nicht gefunden")
        del self.data["items"][entry_id]
        self.save()

def main():
    if len(sys.argv) < 4:
        sys.exit(1)
    
    path = sys.argv[1]
    command = sys.argv[2]
    args = sys.argv[3:]

    try:
        cal = Calendar(path)
        if command == "add":
            if len(args) != 2: raise ValueError("Fehlerhafte Argumente")
            cal.add(args[0], args[1])
        elif command == "list":
            for item in cal.list_items():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif command == "move":
            if len(args) != 2: raise ValueError("Fehlerhafte Argumente")
            cal.move(int(args[0]), args[1])
        elif command == "remove":
            if len(args) != 1: raise ValueError("Fehlerhafte Argumente")
            cal.remove(int(args[0]))
        else:
            raise ValueError("Unbekannter Befehl")
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
