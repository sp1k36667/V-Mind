import sys
import json
import os
import re
from datetime import datetime

class Calendar:
    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                if not isinstance(data["next_id"], int) or not isinstance(data["items"], dict):
                    raise ValueError("Invalid format")
                self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            raise ValueError("Invalid date format")
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid date value")

    def add(self, title, date_str):
        if not title or title.isspace():
            raise ValueError("Empty title")
        self._validate_date(date_str)
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"title": title, "date": date_str}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        items = []
        for idx, val in self.data["items"].items():
            items.append({"id": int(idx), "title": val["title"], "date": val["date"]})
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, entry_id, date_str):
        if entry_id not in self.data["items"]:
            raise ValueError("ID not found")
        self._validate_date(date_str)
        self.data["items"][entry_id]["date"] = date_str
        self._save()

    def remove(self, entry_id):
        if entry_id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][entry_id]
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
            cal.move(int(params[0]), params[1])
        elif command == "remove":
            if len(params) != 1: raise ValueError()
            cal.remove(int(params[0]))
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
