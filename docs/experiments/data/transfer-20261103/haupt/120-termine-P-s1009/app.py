import sys
import json
import os
import re

class Calendar:
    def __init__(self, path):
        self.path = path
        self.data = self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return {"next_id": 1, "items": {}}
        try:
            with open(self.path, 'r') as f:
                data = json.load(f)
                if "next_id" not in data or "items" not in data:
                    raise ValueError
                return data
        except (json.JSONDecodeError, ValueError):
            raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            raise ValueError("Invalid date format")
        try:
            # Simple validation of components
            y, m, d = map(int, date_str.split('-'))
            if not (1 <= m <= 12) or not (1 <= d <= 31):
                raise ValueError
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
        for idx, content in self.data["items"].items():
            items.append({"id": int(idx), **content})
        
        # Sort by date, then by ID
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, entry_id, date):
        idx_str = str(entry_id)
        if idx_str not in self.data["items"]:
            raise ValueError("ID not found")
        self._validate_date(date)
        
        self.data["items"][idx_str]["date"] = date
        self._save()

    def remove(self, entry_id):
        idx_str = str(entry_id)
        if idx_str not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][idx_str]
        self._save()

def main():
    try:
        if len(sys.argv) < 4:
            sys.exit(1)
        
        path = sys.argv[1]
        command = sys.argv[2]
        args = sys.argv[3:]
        
        cal = Calendar(path)
        
        if command == "add":
            if len(args) != 2: raise ValueError()
            cal.add(args[0], args[1])
        elif command == "list":
            for item in cal.list():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif command == "move":
            if len(args) != 2: raise ValueError()
            cal.move(int(args[0]), args[1])
        elif command == "remove":
            if len(args) != 1: raise ValueError()
            cal.remove(int(args[0]))
        else:
            sys.exit(1)
            
    except (ValueError, IndexError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
