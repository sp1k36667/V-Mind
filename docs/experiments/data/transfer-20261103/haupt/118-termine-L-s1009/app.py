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
                raise ValueError("Corrupted file")

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            raise ValueError("Invalid date format")
        try:
            # Simple validation via split to avoid importing datetime
            parts = date_str.split('-')
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            if not (1 <= month <= 12) or not (1 <= day <= 31):
                raise ValueError()
        except:
            raise ValueError("Invalid date")

    def add(self, title, date_str):
        if not title or title.isspace():
            raise ValueError("Empty title")
        self._validate_date(date_str)
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"title": title, "date": date_str}
        self.data["next_id"] += 1
        self.save()
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
        self.save()

    def remove(self, id_str):
        idx = int(id_str)
        if str(idx) not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(idx)]
        self.save()

def main():
    args = sys.argv[1:]
    if len(args) < 3:
        sys.exit(1)
    
    path = args[1]
    cmd = args[2]
    
    try:
        cal = Calendar(path)
        if cmd == "add":
            if len(args) < 5: raise ValueError()
            cal.add(args[3], args[4])
        elif cmd == "list":
            for item in cal.list_items():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif cmd == "move":
            if len(args) < 5: raise ValueError()
            cal.move(args[3], args[4])
        elif cmd == "remove":
            if len(args) < 4: raise ValueError()
            cal.remove(args[3])
        else:
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write("Error: " + str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
