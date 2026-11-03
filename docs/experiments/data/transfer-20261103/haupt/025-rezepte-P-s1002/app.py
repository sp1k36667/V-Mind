import sys
import json
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
            raise ValueError("Empty title")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        
        recipe_id = self.data["next_id"]
        self.data["items"][recipe_id] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self._save()
        return recipe_id

    def list(self):
        items = []
        for rid, content in self.data["items"].items():
            items.append({"id": rid, "title": content["title"], "minutes": content["minutes"]})
        return sorted(items, key=lambda x: x["id"])

    def set_minutes(self, recipe_id, minutes):
        if recipe_id not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        self.data["items"][recipe_id]["minutes"] = minutes
        self._save()

    def remove(self, recipe_id):
        if recipe_id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][recipe_id]
        self._save()

def main():
    if len(sys.argv) < 4:
        sys.exit(1)
    
    path = sys.argv[1]
    command = sys.argv[2]
    args = sys.argv[3:]

    try:
        book = RecipeBook(path)
        if command == "add":
            if len(args) < 2: raise ValueError()
            tid, mins = args[0], int(args[1])
            book.add(tid, mins)
        elif command == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif command == "set":
            if len(args) < 2: raise ValueError()
            rid, mins = int(args[0]), int(args[1])
            book.set_minutes(rid, mins)
        elif command == "remove":
            if len(args) < 1: raise ValueError()
            rid = int(args[0])
            book.remove(rid)
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
