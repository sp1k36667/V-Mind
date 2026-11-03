import sys
import json
import os

class RecipeBook:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    self.data = json.load(f)
                if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                    raise ValueError("Invalid format")
                if not isinstance(self.data["next_id"], int):
                    raise ValueError("Invalid next_id")
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError("Title required")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys(), key=int)
        result = []
        for sid in sorted_ids:
            item = self.data["items"][sid]
            result.append({"id": int(sid), "title": item["title"], "minutes": item["minutes"]})
        return result

    def set_minutes(self, rid, minutes):
        if str(rid) not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        self.data["items"][str(rid)]["minutes"] = minutes
        self._save()

    def remove(self, rid):
        if str(rid) not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(rid)]
        self._save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        
        path = args[1]
        cmd = args[2]
        book = RecipeBook(path)

        if cmd == "add":
            title = args[3]
            minutes = int(args[4])
            book.add(title, minutes)
        elif cmd == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif cmd == "set":
            rid = int(args[3])
            minutes = int(args[4])
            book.set_minutes(rid, minutes)
        elif cmd == "remove":
            rid = int(args[3])
            book.remove(rid)
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
