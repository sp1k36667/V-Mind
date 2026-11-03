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
                if "next_id" not in data or "items" not in data:
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

    def list_items(self):
        items = []
        for i_id, content in self.data["items"].items():
            items.append({"id": int(i_id), **content})
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, i_id, date_str):
        i_id = int(i_id)
        if i_id not in self.data["items"]:
            raise ValueError("ID not found")
        date_str = self._validate_date(date_str)
        self.data["items"][i_id]["date"] = date_str
        self.save()

    def remove(self, i_id):
        i_id = int(i_id)
        if i_id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][i_id]
        self.save()

def main():
    args = sys.argv[1:]
    if len(args) < 3:
        sys.exit(1)
    
    file_path = args[0]
    command = args[1]
    params = args[2:]

    try:
        cal = Calendar(file_path)
        if command == "add":
            if len(params) != 2: raise ValueError()
            cal.add(params[0], params[1])
        elif command == "list":
            for item in cal.list_items():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif command == "move":
            if len(params) != 2: raise ValueError()
            cal.move(params[0], params[1])
        elif command == "remove":
            if len(params) != 1: raise ValueError()
            cal.remove(params[0])
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
