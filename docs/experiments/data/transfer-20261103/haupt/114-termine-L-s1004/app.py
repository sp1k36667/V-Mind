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
                    if "next_id" not in self.data or "items" not in self.data:
                        raise ValueError("Invalid format")
                    # Ensure IDs are handled correctly
                    for k in self.data["items"]:
                        if k.isdigit():
                            self.data["next_id"] = max(self.data["next_id"], int(k) + 1)
                        else:
                            self.data["next_id"] = max(self.data["next_id"], int(k) + 1)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error: Corrupted file", file=sys.stderr)
                sys.exit(1)

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            raise ValueError("Invalid date format")
        try:
            # Basic check if date is valid (e.g. no Feb 30)
            parts = date_str.split("-")
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            if not (1 <= m <= 12): raise ValueError()
            if not (1 <= d <= 31): raise ValueError()
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

    def list_items(self):
        items = []
        for k, v in self.data["items"].items():
            items.append({"id": int(k), "title": v["title"], "date": v["date"]})
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

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(1)
    
    path = args[0]
    cmd = args[1]
    
    try:
        cal = Calendar(path)
        if cmd == "add" and len(args) >= 3:
            title = args[2]
            date = args[3]
            cal.add(title, date)
        elif cmd == "list":
            for item in cal.list_items():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif cmd == "move" and len(args) >= 4:
            cal.move(args[2], args[3])
        elif cmd == "remove" and len(args) >= 3:
            cal.remove(args[2])
        else:
            sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
