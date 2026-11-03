import sys
import json
import os
import re

class Calendar:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                    if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                        raise ValueError("Invalid format")
                    self.data = data
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Damaged JSON file")

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            raise ValueError("Invalid date format")
        try:
            # Check if date is valid (e.g., not 2023-02-30)
            [int(x) for x in date_str.split("-")]
            # Simple check for month/day ranges
            parts = date_str.split("-")
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            if m < 1 or m > 12 or d < 1 or d > 31: raise ValueError()
        except:
            raise ValueError("Invalid date")

    def add(self, title, date):
        if not title or title.isspace():
            raise ValueError("Title cannot be empty")
        self._validate_date(date)
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"id": new_id, "title": title, "date": date}
        self.data["next_id"] += 1
        self.save()
        return new_id

    def list(self):
        items = []
        for k, v in self.data["items"].items():
            items.append(v)
        # Sort by date, then by ID
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, entry_id, date):
        s_id = str(entry_id)
        if s_id not in self.data["items"]:
            raise ValueError("ID not found")
        self._validate_date(date)
        self.data["items"][s_id]["date"] = date
        self.save()

    def remove(self, entry_id):
        s_id = str(entry_id)
        if s_id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][s_id]
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
            if len(args) < 5: raise ValueError()
            cal.move(int(args[3]), args[4])
        elif cmd == "remove":
            if len(args) < 4: raise ValueError()
            cal.remove(int(args[3]))
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"{str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
