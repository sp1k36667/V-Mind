import sys
import json
import os
import datetime

class Calendar:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    self.data = json.load(f)
                    if not isinstance(self.data.get("next_id"), int) or \
                       not isinstance(self.data.get("items"), dict):
                        raise ValueError
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            raise ValueError("Invalid date format")

    def add(self, title, date_str):
        if not title or title.isspace():
            raise ValueError("Title cannot be empty")
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
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        path = args[0]
        cmd = args[1]
        params = args[2:]
        
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
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
