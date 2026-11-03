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
                    raw = json.load(f)
                    if not isinstance(raw, dict) or "next_id" not in raw or "items" not in raw:
                        raise ValueError("Invalid format")
                    self.data = raw
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted JSON file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            raise ValueError("Invalid date format")
        try:
            # Simple check for valid date components
            y, m, d = map(int, date_str.split('-'))
            if not (1 <= m <= 12) or not (1 <= d <= 31):
                raise ValueError()
        except:
            raise ValueError("Invalid date values")

    def add(self, title, date_str):
        if not title or title.isspace():
            raise ValueError("Title cannot be empty")
        self._validate_date(date_str)
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"title": title, "date": date_str}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list_items(self):
        items = []
        for k, v in self.data["items"].items():
            items.append({"id": int(k), **v})
        
        # Sort by date, then by ID
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, id_str, date_str):
        idx = int(id_str)
        if str(idx) not in self.data["items"]:
            raise ValueError("ID not found")
        self._validate_date(date_str)
        
        self.data["items"][str(idx)]["date"] = date_str
        self._save()

    def remove(self, id_str):
        idx = int(id_str)
        if str(idx) not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(idx)]
        self._save()

def main():
    args = sys.argv[1:]
    if len(args) < 3:
        sys.exit(1)
    
    path = args[0]
    command = args[1]
    
    try:
        cal = Calendar(path)
        if command == "add":
            if len(args) < 4: raise ValueError("Missing args")
            cal.add(args[2], args[3])
        elif command == "list":
            for item in cal.list_items():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif command == "move":
            if len(args) < 4: raise ValueError("Missing args")
            cal.move(args[2], args[3])
        elif command == "remove":
            if len(args) < 3: raise ValueError("Missing args")
            cal.remove(args[2])
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
