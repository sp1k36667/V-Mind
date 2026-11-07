import json
import sys
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
                if not isinstance(data["next_id"], int) or not isinstance(data["items"], dict):
                    raise ValueError("Invalid format")
                self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self.save()

    def save(self):
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
        self.save()
        return new_id

    def list(self):
        items = []
        for idx, val in self.data["items"].items():
            if not isinstance(idx, int):
                raise ValueError("Corrupted file")
            items.append({"id": idx, **val})
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, id_val, date_str):
        try:
            idx = int(id_val)
        except ValueError:
            raise ValueError("Invalid ID")
        if idx not in self.data["items"]:
            raise ValueError("ID not found")
        date_str = self._validate_date(date_str)
        self.data["items"][idx]["date"] = date_str
        self.save()

    def remove(self, id_val):
        try:
            idx = int(id_val)
        except ValueError:
            raise ValueError("Invalid ID")
        if idx not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][idx]
        self.save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        path = args[0]
        cmd = args[1]
        cal = Calendar(path)
        
        if cmd == "add":
            if len(args) < 4: raise ValueError("Missing args")
            cal.add(args[2], args[3])
        elif cmd == "list":
            for item in cal.list():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif cmd == "move":
            if len(args) < 4: raise ValueError("Missing args")
            cal.move(args[2], args[3])
        elif cmd == "remove":
            if len(args) < 3: raise ValueError("Missing args")
            cal.remove(args[2])
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
