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
                self.next_id = data["next_id"]
                self.items = data["items"]
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")
        else:
            self.next_id = 1
            self.items = {}
        self.save()

    def save(self):
        with open(self.path, 'w') as f:
            json.dump({"next_id": self.next_id, "items": self.items}, f)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError("Title required")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        
        recipe_id = self.next_id
        self.items[str(recipe_id)] = {"title": title, "minutes": minutes}
        self.next_id += 1
        self.save()
        return recipe_id

    def list_recipes(self):
        sorted_ids = sorted(self.items.keys(), key=int)
        result = []
        for rid in sorted_ids:
            item = self.items[rid]
            result.append({"id": int(rid), "title": item["title"], "minutes": item["minutes"]})
        return result

    def set_minutes(self, recipe_id, minutes):
        if not str(recipe_id) in self.items:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        self.items[str(recipe_id)]["minutes"] = minutes
        self.save()

    def remove(self, recipe_id):
        if str(recipe_id) not in self.items:
            raise ValueError("ID not found")
        del self.items[str(recipe_id)]
        self.save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        
        path = args[1]
        cmd = args[2].split()
        book = RecipeBook(path)

        if cmd[0] == "add":
            if len(cmd) < 4: raise ValueError()
            book.add(cmd[3], int(cmd[4]))
        elif cmd[0] == "list":
            for r in book.list_recipes():
                print(f"{r['id']} {r['minutes']} min {r['title']}")
        elif cmd[0] == "set":
            book.set_minutes(int(cmd[1]), int(cmd[2]))
        elif cmd[0] == "remove":
            book.remove(int(cmd[1]))
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
