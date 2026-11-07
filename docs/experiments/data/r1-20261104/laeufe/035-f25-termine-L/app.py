import sys
import json
import os
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
                self.data = data
            except (json.JSONDecodeError, ValueError) as e:
                if "Invalid format" in str(e):
                    raise ValueError("Damaged JSON file")
                raise ValueError("Damaged JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

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
        if not title or title.isspace():
            raise ValueError("Title cannot be empty")
        date_str = self._validate_date(date_str)
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"title": title, "date": date_str}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        items = []
        for id_val, val in self.data["items"].items():
            items.append({"id": int(id_val), **val})
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, id_str, date_str):
        try:
            idx = int(id_str)
        except ValueError:
            raise ValueError("Invalid ID")
        if idx not in self.data["items"]:
            raise ValueError("ID not found")
        date_str = self._validate_date(date_str)
        self.data["items"][idx]["date"] = date_str
        self._save()

    def remove(self, id_str):
        try:
            idx = int(id_str)
        except ValueError:
            raise ValueError("Invalid ID")
        if idx not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][idx]
        self._save()

def main():
    if len(sys.argv) < 4 or sys.argv[1] != "--file":
        print("Usage: python3 app.py --file PATH COMMAND [ARGS]", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[2]
    cmd = sys.argv[3]
    args = sys.argv[4:]

    try:
        cal = Calendar(path)
        if cmd == "add":
            if len(args) != 2: raise ValueError("Missing arguments")
            cal.add(args[0], args[1])
        elif cmd == "list":
            for item in cal.list():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif cmd == "move":
            if len(args) != 2: raise ValueError("Missing arguments")
            cal.move(args[0], args[1])
        elif cmd == "remove":
            if len(args) != 1: raise ValueError("Missing arguments")
            cal.remove(args[0])
        else:
            print("Unknown command", file=sys.stderr)
            sys.exit(1)
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
