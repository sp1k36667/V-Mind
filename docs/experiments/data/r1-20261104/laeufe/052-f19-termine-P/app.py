import json
import sys
import os
from datetime import datetime

class Calendar:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    loaded = json.load(f)
                    if not isinstance(loaded, dict) or \
                       "next_id" not in loaded or \
                       not isinstance(loaded["next_id"], int) or \
                       "items" not in loaded or \
                       not isinstance(loaded["items"], dict):
                        raise ValueError
                    self.data = loaded
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Beschädigte Datei.")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            raise ValueError("Ungültiges Datum.")

    def add(self, title, date_str):
        if not title or title.isspace():
            raise ValueError("Leerer Titel.")
        date_str = self._validate_date(date_str)
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"title": title, "date": date_str}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        items = []
        for idx, val in self.data["items"].items():
            items.append({"id": int(idx), **val})
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, id_str, date_str):
        try:
            idx = int(id_str)
        except ValueError:
            raise ValueError("Ungültige ID.")
        if str(idx) not in self.data["items"]:
            raise ValueError("ID nicht gefunden.")
        date_str = self._validate_date(date_str)
        self.data["items"][str(idx)]["date"] = date_str
        self._save()

    def remove(self, id_str):
        try:
            idx = int(id_str)
        except ValueError:
            raise ValueError("Ungültige ID.")
        if str(idx) not in self.data["items"]:
            raise ValueError("ID nicht gefunden.")
        del self.data["items"][str(idx)]
        self._save()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.stderr.write("Fehlende Argumente\n")
        sys.exit(1)
    
    file_path = sys.argv[1]
    command = sys.argv[2]
    args = sys.argv[3:]

    try:
        cal = Calendar(file_path)
        if command == "add" and len(args) == 2:
            cal.add(args[0], args[1])
        elif command == "list":
            for item in cal.list():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif command == "move" and len(args) == 2:
            cal.move(args[0], args[1])
        elif command == "remove" and len(args) == 1:
            cal.remove(args[0])
        else:
            sys.stderr.write("Unbekannter Befehl oder falsche Argumente\n")
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
