import sys
import json
import os
import re

def validate_date(date_str):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise ValueError("Ungültiges Datumsformat. Erwartet: JJJJ-MM-TT.")
    try:
        # Einfache Validierung über datetime-ähnliche Logik ohne Import
        parts = date_str.split("-")
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        if not (1 <= month <= 12) or not (1 <= day <= 31):
            raise ValueError
        return True
    except ValueError:
        raise ValueError("Ungültiges Datum.")

class Calendar:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    content = f.read()
                    if not content.strip():
                        raise ValueError("Datei leer.")
                    loaded = json.loads(content)
                    if not isinstance(loaded, dict) or "next_id" not in loaded or "items" not in loaded:
                        raise ValueError("Ungültiges Format.")
                    self.data = loaded
                    # Sicherstellen, dass IDs in items als Strings behandelt werden (JSON Standard)
                    # Aber intern prüfen wir auf Existenz
            except (json.JSONDecodeError, ValueError) as e:
                raise ValueError(f"Datei beschädigt: {e}")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, date):
        if not title or title.isspace():
            raise ValueError("Titel darf nicht leer sein.")
        validate_date(date)
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"id": new_id, "title": title, "date": date}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list_items(self):
        items = []
        for k, v in self.data["items"].items():
            items.append(v)
        # Sortiere nach Datum, dann nach ID
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, id_str, date):
        if id_str not in self.data["items"]:
            raise ValueError(f"ID {id_str} nicht gefunden.")
        validate_date(date)
        self.data["items"][id_str]["date"] = date
        self._save()

    def remove(self, id_str):
        if id_str not in self.data["items"]:
            raise ValueError(f"ID {id_str} nicht gefunden.")
        del self.data["items"][id_str]
        self._save()

def main():
    args = sys.argv[1:]
    if len(args) < 2:
        return
    
    file_path = args[0]
    command = args[1]
    
    try:
        cal = Calendar(file_path)
        
        if command == "add":
            if len(args) < 4:
                raise ValueError("Fehlende Argumente für 'add'.")
            cal.add(args[2], args[3])
        elif command == "list":
            for item in cal.list_items():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif command == "move":
            if len(args) < 4:
                raise ValueError("Fehlende Argumente für 'move'.")
            cal.move(args[2], args[3])
        elif command == "remove":
            if len(args) < 3:
                raise ValueError("Fehlende Argumente für 'remove'.")
            cal.remove(args[2])
        else:
            raise ValueError(f"Unbekannter Befehl: {command}")
            
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write("Unerwarteter Fehler: " + str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
