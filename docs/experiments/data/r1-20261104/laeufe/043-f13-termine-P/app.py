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
                    data = json.load(f)
                    if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                        raise ValueError
                    if not isinstance(data["next_id"], int) or not isinstance(data["items"], dict):
                        raise ValueError
                    self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Beschädigte Datei")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            raise ValueError("Ungültiges Datum")

    def add(self, title, date_str):
        if not title or title.isspace():
            raise ValueError("Leerer Titel")
        date_str = self._validate_date(date_str)
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"title": title, "date": date_str}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        items = []
        for k, v in self.data["items"].items():
            items.append({"id": k, "title": v["title"], "date": v["date"]})
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, id_val, date_str):
        try:
            id_int = int(id_val)
        except ValueError:
            raise ValueError("Ungültige ID")
        if id_int not in self.data["items"]:
            raise ValueError("ID nicht gefunden")
        date_str = self._validate_date(date_str)
        self.data["items"][id_int]["date"] = date_str
        self._save()

    def remove(self, id_val):
        try:
            id_int = int(id_val)
        except ValueError:
            raise ValueError("Ungültige ID")
        if id_int not in self.data["items"]:
            raise ValueError("ID nicht gefunden")
        del self.data["items"][id_int]
        self._save()

def main():
    args = sys.argv[1:]
    if len(args) < 3:
        sys.exit(1)
    
    file_path = args[0]
    command = args[1]
    params = args[2:]

    try:
        cal = Calendar(file_path)
        if command == "add":
            if len(params) != 2: raise ValueError()
            cal.add(params[0], params[1])
        elif command == "list":
            for item in cal.list():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif command == "move":
            if len(params) != 2: raise ValueError()
            cal.move(params[0], params[1])
        elif command == "remove":
            if len(params) != 1: raise ValueError()
            cal.remove(params[0])
        else:
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception:
        sys.stderr.write("Fehler\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
