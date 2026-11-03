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
                if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                    raise ValueError("Invalid format")
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file")

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
            raise ValueError("Empty title")
        date_str = self._validate_date(date_str)
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"title": title, "date": date_str}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        items = []
        for id, content in self.data["items"].items():
            items.append({"id": id, "title": content["title"], "date": content["date"]})
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, id, date_str):
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        date_str = self._validate_date(date_str)
        self.data["items"][id]["date"] = date_str
        self._save()

    def remove(self, id):
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id]
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
            if len(args) < 5: raise ValueError("Missing args")
            cal.add(args[3], args[4])
        elif cmd == "list":
            for item in cal.list():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif cmd == "move":
            if len(args) < 5: raise ValueError("Missing args")
            cal.move(int(args[3]), args[4])
        elif cmd == "remove":
            if len(args) < 4: raise ValueError("Missing args")
            cal.remove(int(args[3]))
        else:
            print("Unknown command", file=sys.stderr)
            sys.exit(1)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
