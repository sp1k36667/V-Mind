import sys
import json
import os
import re

class Calendar:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    self.data = json.load(f)
                if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                    raise ValueError("Invalid format")
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            raise ValueError("Invalid date format")
        try:
            # Basic check for valid dates
            parts = date_str.split("-")
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            if not (1 <= month <= 12) or not (1 <= day <= 31):
                raise ValueError()
        except:
            raise ValueError("Invalid date")

    def add(self, title, date):
        if not title or title.isspace():
            raise ValueError("Empty title")
        self._validate_date(date)
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"title": title, "date": date}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        items = []
        for key, val in self.data["items"].items():
            items.append({"id": int(key), **val})
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, id_str, date):
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        self._validate_date(date)
        self.data["items"][id_str]["date"] = date
        self._save()

    def remove(self, id_str):
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id_str]
        self._save()

def main():
    args = sys.argv[1:]
    if len(args) < 3:
        print("Usage: python3 app.py --file PATH COMMAND [ARGS]", file=sys.stderr)
        sys.exit(1)
    
    if args[0] != "--file":
        print("Usage: python3 app.py --file PATH COMMAND [ARGS]", file=sys.stderr)
        sys.exit(1)

    path = args[1]
    cmd = args[2]
    
    try:
        cal = Calendar(path)
        if cmd == "add":
            if len(args) < 5: raise ValueError()
            cal.add(args[3], args[4])
        elif cmd == "list":
            for item in cal.list():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif cmd == "move":
            if len(args) < 5: raise ValueError()
            cal.move(args[3], args[4])
        elif cmd == "remove":
            if len(args) < 4: raise ValueError()
            cal.remove(args[3])
        else:
            print("Unknown command", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
