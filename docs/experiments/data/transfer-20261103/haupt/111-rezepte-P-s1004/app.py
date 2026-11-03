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
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self.save()

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError("Invalid title")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        
        recipe_id = self.data["next_id"]
        self.data["items"][recipe_id] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self.save()
        return recipe_id

    def list_recipes(self):
        items = []
        for rid, content in self.data["items"].items():
            items.append({"id": rid, "title": content["title"], "minutes": content["minutes"]})
        return sorted(items, key=lambda x: x["id"])

    def set_minutes(self, rid, minutes):
        if rid not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        self.data["items"][rid]["minutes"] = minutes
        self.save()

    def remove(self, rid):
        if rid not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][rid]
        self.save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        
        path = args[0]
        cmd = args[1]
        params = args[2:]
        
        book = RecipeBook(path)
        
        if cmd == "add":
            if len(params) < 2: raise ValueError()
            rid = book.add(params[0], int(params[1]))
            print(rid)
        elif cmd == "list":
            for r in book.list_recipes():
                print(f"{r['id']} {r['minutes']} min {r['title']}")
        elif cmd == "set":
            if len(params) < 2: raise ValueError()
            book.set_minutes(int(params[0]), int(params[1]))
        elif cmd == "remove":
            if len(params) < 1: raise ValueError()
            book.remove(int(params[0]))
        else:
            sys.exit(1)
            
    except Exception as e:
        sys.stderr.write(f"{type(e).__name__}: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
