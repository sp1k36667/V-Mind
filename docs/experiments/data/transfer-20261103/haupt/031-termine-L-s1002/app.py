import sys
import json
import os

class Calendar:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    content = json.load(f)
                    if not isinstance(content, dict) or "next_id" not in content or "items" not in content:
                        raise ValueError()
                    self.data = content
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("File is corrupted.")

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        try:
            import datetime
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def add(self, title, date_str):
        if not title or title.isspace():
            raise ValueError("Title cannot be empty.")
        if not self._validate_date(date_str):
            raise ValueError("Invalid date format.")
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"title": title, "date": date_str}
        self.data["next_id"] += 1
        self.save()
        return new_id

    def list_items(self):
        items = []
        for key, val in self.data["items"].items():
            items.append({"id": int(key), "title": val["title"], "date": val["date"]})
        
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, id_str, date_str):
        idx = int(id_str)
        if str(idx) not in self.data["items"]:
            raise ValueError("ID not found.")
        if not self._validate_date(date_str):
            raise ValueError("Invalid date format.")
        
        self.data["items"][str(idx)]["date"] = date_str
        self.save()

    def remove(self, id_str):
        idx = int(id_str)
        if str(idx) not in self.data["items"]:
            raise ValueError("ID not found.")
        del self.data["items"][str(idx)]
        self.save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 2:
            return
        
        path = args[0]
        cmd = args[1]
        cal = Calendar(path)

        if cmd == "add":
            if len(args) < 4: raise ValueError()
            cal.add(args[2], args[3])
        elif cmd == "list":
            for item in cal.list_items():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif cmd == "move":
            if len(args) < 4: raise ValueError()
            cal.move(args[2], args[3])
        elif cmd == "remove":
            if len(args) < 3: raise ValueError()
            cal.remove(args[2])
        else:
            raise ValueError()
    except (ValueError, IndexError, TypeError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
