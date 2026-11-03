import sys
import json
import os

class RecipeBook:
    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.data = data
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError("Title required")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        
        recipe_id = self.data["next_id"]
        self.data["items"][recipe_id] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self._save()
        return recipe_id

    def list(self):
        res = []
        for rid in sorted(self.data["items"].keys()):
            item = self.data["items"][rid]
            res.append({"id": rid, "title": item["title"], "minutes": item["minutes"]})
        return res

    def set_minutes(self, rid, minutes):
        if rid not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        self.data["items"][rid]["minutes"] = minutes
        self._save()

    def remove(self, rid):
        if rid not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][rid]
        self._save()

def main():
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(1)
    
    file_path = args[0]
    command = args[1]
    
    try:
        book = RecipeBook(file_path)
        if command == "add":
            if len(args) < 4: raise ValueError()
            rid = book.add(args[2], int(args[3]))
            print(rid)
        elif command == "list":
            for r in book.list():
                print(f"{r['id']} {r['minutes']} min {r['title']}")
        elif command == "set":
            if len(args) < 4: raise ValueError()
            book.set_minutes(int(args[2]), int(args[3]))
        elif command == "remove":
            if len(args) < 3: raise ValueError()
            book.remove(int(args[2]))
        else:
            sys.exit(1)
    except (ValueError, IndexError, TypeError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
