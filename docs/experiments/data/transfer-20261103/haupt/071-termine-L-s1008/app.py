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
                    content = f.read()
                    if not content.strip():
                        raise ValueError("Empty file")
                    self.data = json.loads(content)
                    if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                        raise ValueError("Invalid format")
                    if not isinstance(self.data["next_id"], int) or not isinstance(self.data["items"], dict):
                        raise ValueError("Invalid types")
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            raise ValueError("Invalid date format")
        try:
            year, month, day = map(int, date_str.split("-"))
            if not (1 <= month <= 12) or not (1 <= day <= 31):
                raise ValueError()
            # Basic check, doesn't handle leap years perfectly but covers most invalid
            return True
        except:
            raise ValueError("Invalid date")

    def add(self, title, date):
        if not title or title.isspace():
            raise ValueError("Title cannot be empty")
        self._validate_date(date)
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"title": title, "date": date}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        items = []
        for k, v in self.data["items"].items():
            items.append({"id": int(k), **v})
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, id_str, date):
        idx = int(id_str)
        if str(idx) not in self.data["items"]:
            raise ValueError("ID not found")
        self._validate_date(date)
        self.data["items"][str(idx)]["date"] = date
        self._save()

    def remove(self, id_str):
        idx = int(id_str)
        if str(idx) not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(idx)]
        self._save()

def main():
    try:
        if len(sys.argv) < 4:
            sys.exit(1)
        path = sys.argv[1]
        cmd = sys.argv[2]
        args = sys.argv[3:]

        cal = Calendar(path)

        if cmd == "add":
            if len(args) != 2: raise ValueError()
            cal.add(args[0], args[1])
        elif cmd == "list":
            for item in cal.list():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif cmd == "move":
            if len(args) != 2: raise ValueError()
            cal.move(args[0], args[1])
        elif cmd == "remove":
            if len(args) != 1: raise ValueError()
            cal.remove(args[0])
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
