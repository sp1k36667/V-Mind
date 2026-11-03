import sys
import json
import os
import re

class Calendar:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    self.data = json.load(f)
                    if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                        raise ValueError
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Beschädigte Datei")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            raise ValueError("Ungültiges Datum")
        try:
            # Check if valid date (e.g. 2023-02-30 is invalid)
            parts = date_str.split("-")
            dt = datetime.datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            return date_str
        except ValueError:
            raise ValueError("Ungültiges Datum")

    def add(self, title, date_str):
        if not title or title.isspace():
            raise ValueError("Titel leer")
        date_str = self._validate_date(date_str)
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"title": title, "date": date_str}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        items = []
        for k, v in self.data["items"].items():
            items.append({"id": int(k), **v})
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, id_str, date_str):
        idx = int(id_str)
        if str(idx) not in self.data["items"]:
            raise ValueError("ID nicht gefunden")
        date_str = self._validate_date(date_str)
        self.data["items"][str(idx)]["date"] = date_str
        self._save()

    def remove(self, id_str):
        idx = int(id_str)
        if str(idx) not in self.data["items"]:
            raise ValueError("ID nicht gefunden")
        del self.data["items"][str(idx)]
        self._save()

import datetime

def main():
    try:
        if len(sys.argv) < 4:
            sys.exit(0)
        path = sys.argv[1]
        cmd = sys.argv[2]
        args = sys.argv[3:]
        
        cal = Calendar(path)
        
        if cmd == "add":
            if len(args) < 2: raise ValueError()
            cal.add(args[0], args[1])
        elif cmd == "list":
            for item in cal.list():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif cmd == "move":
            cal.move(args[0], args[1])
        elif cmd == "remove":
            cal.remove(args[0])
        else:
            pass
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
