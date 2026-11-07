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
                    content = json.load(f)
                    if not isinstance(content, dict) or "next_id" not in content or "items" not in content:
                        raise ValueError
                    self.data = content
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Invalid JSON file.")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except (ValueError, TypeError):
            raise ValueError("Invalid date format.")

    def add(self, title, date_str):
        if not title or title.isspace():
            raise ValueError("Title cannot be empty.")
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

    def move(self, id_raw, date_str):
        try:
            id_val = int(id_raw)
            id_str = str(id_val)
        except (ValueError, TypeError):
            raise ValueError("Invalid ID.")
        
        if id_str not in self.data["items"]:
            raise ValueError("ID not found.")
        
        date_str = self._validate_date(date_str)
        self.data["items"][id_str]["date"] = date_str
        self._save()

    def remove(self, id_raw):
        try:
            id_val = int(id_raw)
            id_str = str(id_val)
        except (ValueError, TypeError):
            raise ValueError("Invalid ID.")
            
        if id_str not in self.data["items"]:
            raise ValueError("ID not found.")
        del self.data["items"][id_str]
        self._save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        path = args[1]
        cmd = args[2]
        params = args[3:]

        cal = Calendar(path)

        if cmd == "add":
            if len(params) != 2: raise ValueError
            cal.add(params[0], params[1])
        elif cmd == "list":
            for item in cal.list():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif cmd == "move":
            if len(params) != 2: raise ValueError
            cal.move(params[0], params[1])
        elif cmd == "remove":
            if len(params) != 1: raise ValueError
            cal.remove(params[0])
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
