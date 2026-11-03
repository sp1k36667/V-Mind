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
            with open(self.path, "r") as f:
                data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError()
                return data
        except (json.JSONDecodeError, ValueError, TypeError):
            raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            raise ValueError("Invalid date format")
        try:
            import datetime
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid date")

    def add(self, title, date_str):
        if not title or title.isspace():
            raise ValueError("Title cannot be empty")
        self._validate_date(date_str)
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"title": title, "date": date_str}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        items = []
        for id_str, content in self.data["items"].items():
            items.append({"id": int(id_str), **content})
        
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, id_val, date_str):
        id_str = str(id_val)
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        self._validate_date(date_str)
        self.data["items"][id_str]["date"] = date_str
        self._save()

    def remove(self, id_val):
        id_str = str(id_val)
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id_str]
        self._save()

def main():
    args = sys.argv[1:]
    if len(args) < 3:
        return
    
    path = args[1]
    cmd = args[2]
    params = args[3:]

    try:
        cal = Calendar(path)
        if cmd == "add":
            if len(params) != 2: raise ValueError()
            cal.add(params[0], params[1])
        elif cmd == "list":
            for item in cal.list():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif cmd == "move":
            if len(params) != 2: raise ValueError()
            cal.move(int(params[0]), params[1])
        elif cmd == "remove":
            if len(params) != 1: raise ValueError()
            cal.remove(int(params[0]))
        else:
            raise ValueError("Unknown command")
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
