import sys
import json
import os
from datetime import datetime

class Calendar:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    self.data = json.load(f)
                if not isinstance(self.data.get("next_id"), int) or \
                   not isinstance(self.data.get("items"), dict):
                    raise ValueError("Invalid format")
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            raise ValueError("Invalid date format")

    def add(self, title, date_str):
        if not title or not title.strip():
            raise ValueError("Title required")
        date_str = self._validate_date(date_str)
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"title": title, "date": date_str}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list_items(self):
        items = []
        for idx, content in self.data["items"].items():
            items.append({"id": int(idx), **content})
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, entry_id, date_str):
        if entry_id not in self.data["items"]:
            raise ValueError("ID not found")
        date_str = self._validate_date(date_str)
        self.data["items"][entry_id]["date"] = date_str
        self._save()

    def remove(self, entry_id):
        if entry_id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][entry_id]
        self._save()

def main():
    if len(sys.argv) < 4:
        sys.exit(1)
    
    file_path = sys.argv[1]
    command = sys.argv[2]
    args = sys.argv[3:]

    try:
        cal = Calendar(file_path)
        if command == "add":
            if len(args) != 2: raise ValueError("Usage: add TITLE DATE")
            cal.add(args[0], args[1])
        elif command == "list":
            for item in cal.list_items():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif command == "move":
            if len(args) != 2: raise ValueError("Usage: move ID DATE")
            cal.move(int(args[0]), args[1])
        elif command == "remove":
            if len(args) != 1: raise ValueError("Usage: remove ID")
            cal.remove(int(args[0]))
        else:
            raise ValueError("Unknown command")
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
