import sys
import json
import os
import re

class Calendar:
    def __init__(self, path):
        self.path = path
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.next_id = data["next_id"]
                self.items = data["items"]
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Corrupted file")
        else:
            self.next_id = 1
            self.items = {}
        self.save()

    def save(self):
        with open(self.path, 'w') as f:
            json.dump({"next_id": self.next_id, "items": self.items}, f)

    def _validate_date(self, date_str):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
            raise ValueError("Invalid date format")
        try:
            import datetime
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid date value")

    def add(self, title, date_str):
        if not title or title.isspace():
            raise ValueError("Title cannot be empty")
        self._validate_date(date_str)
        new_id = self.next_id
        self.items[str(new_id)] = {"id": new_id, "title": title, "date": date_str}
        self.next_id += 1
        self.save()
        return new_id

    def list(self):
        res = []
        for k, v in self.items.items():
            res.append(v)
        res.sort(key=lambda x: (x["date"], x["id"]))
        return res

    def move(self, id_str, date_str):
        if id_str not in self.items:
            raise ValueError("ID not found")
        self._validate_date(date_str)
        self.items[id_str]["date"] = date_str
        self.save()

    def remove(self, id_str):
        if id_str not in self.items:
            raise ValueError("ID not found")
        del self.items[id_str]
        self.save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(0)
        path = args[0]
        cmd = args[1]
        cal = Calendar(path)

        if cmd == "add":
            if len(args) < 4: raise ValueError("Missing args")
            cal.add(args[2], args[3])
        elif cmd == "list":
            for item in cal.list():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif cmd == "move":
            if len(args) < 4: raise ValueError("Missing args")
            cal.move(args[2], args[3])
        elif cmd == "remove":
            if len(args) < 3: raise ValueError("Missing args")
            cal.remove(args[2])
        else:
            sys.exit(0)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
