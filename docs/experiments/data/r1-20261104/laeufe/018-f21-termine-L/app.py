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
        for i_id, content in self.data["items"].items():
            items.append({"id": int(i_id), **content})
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, i_id, date_str):
        try:
            i_id = int(i_id)
        except ValueError:
            raise ValueError("Invalid ID")
        if i_id not in self.data["items"]:
            raise ValueError("ID not found")
        date_str = self._validate_date(date_str)
        self.data["items"][i_id]["date"] = date_str
        self.save()

    def remove(self, i_id):
        try:
            i_id = int(i_id)
        except ValueError:
            raise ValueError("Invalid ID")
        if i_id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][i_id]
        self.save()

def main():
    args = sys.argv[1:]
    if len(args) < 3 or args[0] != "--file":
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
            if len(args) < 6: raise ValueError()
            cal.move(args[3], args[4])
        elif cmd == "remove":
            if len(args) < 4: raise ValueError()
            cal.remove(args[3])
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
