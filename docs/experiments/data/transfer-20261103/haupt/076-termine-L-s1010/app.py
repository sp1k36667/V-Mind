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
                    self.data = json.load(f)
                if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                    raise ValueError("Invalid format")
                # Ensure keys are handled correctly (json keys are always strings)
                for k in list(self.data["items"].keys()):
                    self.data["items"][int(k)] = self.data["items"].pop(k)
            except (json.JSONDecodeError, ValueError, KeyError, TypeError):
                raise ValueError("Damaged JSON file")

    def _save(self):
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
        self._save()
        return new_id

    def list(self):
        items = []
        for i_id, content in self.data["items"].items():
            items.append({"id": i_id, "title": content["title"], "date": content["date"]})
        # Sort by date, then by ID
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, i_id, date_str):
        if i_id not in self.data["items"]:
            raise ValueError("ID not found")
        date_str = self._validate_date(date_str)
        self.data["items"][i_id]["date"] = date_str
        self._save()

    def remove(self, i_id):
        if i_id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][i_id]
        self._save()

def main():
    args = sys.argv[1:]
    if len(args) < 3:
        sys.exit(1)
    
    file_path = args[0]
    command = args[1]
    
    try:
        cal = Calendar(file_path)
        if command == "add" and len(args) == 4:
            cal.add(args[2], args[3])
        elif command == "list":
            for item in cal.list():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif command == "move" and len(args) == 4:
            cal.move(int(args[2]), args[3])
        elif command == "remove" and len(args) == 3:
            cal.remove(int(args[2]))
        else:
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
