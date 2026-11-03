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
                for k in self.data["items"]:
                    self.data["next_id"] = max(self.data["next_id"], int(k) + 1)
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
        if not title or title.isspace():
            raise ValueError("Title required")
        date_str = self._validate_date(date_str)
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"id": new_id, "title": title, "date": date_str}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        items = []
        for k, v in self.data["items"].items():
            items.append(v)
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, id_str, date_str):
        idx = int(id_str)
        if str(idx) not in self.data["items"]:
            raise ValueError("ID not found")
        date_str = self._validate_date(date_str)
        self.data["items"][str(idx)]["date"] = date_str
        self._save()

    def remove(self, id_str):
        idx = int(id_str)
        if str(idx) not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(idx)]
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
            if len(args) != 2: raise ValueError()
            cal.add(args[0], args[1])
        elif command == "list":
            for item in cal.list():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif command == "move":
            if len(args) != 2: raise ValueError()
            cal.move(args[0], args[1])
        elif command == "remove":
            if len(args) != 1: raise ValueError()
            cal.remove(args[0])
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
