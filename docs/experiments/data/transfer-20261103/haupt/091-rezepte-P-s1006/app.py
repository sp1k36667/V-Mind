import json
import sys
import os

class RecipeBook:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    self.data = json.load(f)
                if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                    raise ValueError("Invalid format")
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
        
        recipe_id = self.data["next_id"]
        self.data["items"][recipe_id] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self._save()
        return recipe_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys())
        results = []
        for rid in sorted_ids:
            item = self.data["items"][rid]
            results.append({"id": rid, "title": item["title"], "minutes": item["minutes"]})
        return results

    def set_minutes(self, recipe_id, minutes):
        if recipe_id not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        self.data["items"][recipe_id]["minutes"] = minutes
        self._save()

    def remove(self, recipe_id):
        if recipe_id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][recipe_id]
        self._save()

def main():
    if len(sys.argv) < 3:
        sys.exit(1)
    
    path = sys.argv[1]
    cmd = sys.argv[2]
    args = sys.argv[3:]

    try:
        book = RecipeBook(path)
        if cmd == "add":
            if len(args) < 2: raise ValueError()
            rid = book.add(args[0], int(args[1]))
            print(rid)
        elif cmd == "list":
            for r in book.list():
                print(f"{r['id']} {r['minutes']} min {r['title']}")
        elif cmd == "set":
            if len(args) < 2: raise ValueError()
            book.set_minutes(int(args[0]), int(args[1]))
        elif cmd == "remove":
            if len(args) < 1: raise ValueError()
            book.remove(int(args[0]))
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
