import sys
import json
import os
import re

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
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            raise ValueError("Invalid date format")
        try:
            # Basic check for valid date components
            y, m, d = map(int, date_str.split("-"))
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
        for k, v in self.data["items"].items():
            items.append({"id": int(k), **v})
        # Sort by date, then by id
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, id_str, date):
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        self._validate_date(date)
        self.data["items"][id_str]["date"] = date
        self._save()

    def remove(self, id_str):
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id_str]
        self._save()

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
            res = cal.add(params[0], params[1])
            print(res)
        elif command == "list":
            for item in cal.list():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif command == "move":
            if len(params) != 2: raise ValueError()
            cal.move(params[0], params[1])
        elif command == "remove":
            if len(params) != 1: raise ValueError()
            cal.remove(params[0])
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
