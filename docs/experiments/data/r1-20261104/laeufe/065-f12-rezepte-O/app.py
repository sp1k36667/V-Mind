import json
import sys
import os

class RecipeBook:
    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError("Corrupted file")
                if not isinstance(data["next_id"], int) or not isinstance(data["items"], dict):
                    raise ValueError("Corrupted file")
                self.data = data
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self.save()

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, minutes):
        if not isinstance(title, str) or not title or title.isspace():
            raise ValueError("Invalid title")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self.save()
        return new_id

    def list(self):
        items = []
        for idx, val in self.data["items"].items():
            if not isinstance(idx, int): raise ValueError("Corrupted file")
            items.append({"id": idx, **val})
        return sorted(items, key=lambda x: x["id"])

    def set_minutes(self, recipe_id, minutes):
        if not isinstance(recipe_id, int) or recipe_id not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        self.data["items"][recipe_id]["minutes"] = minutes
        self.save()

    def remove(self, recipe_id):
        if not isinstance(recipe_id, int) or recipe_id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][recipe_id]
        self.save()

def main():
    if len(sys.argv) < 3:
        sys.stderr.write("Usage: python3 app.py --file PATH COMMAND [ARGS]\n")
        sys.exit(1)
    
    if sys.argv[1] != "--file":
        sys.exit(1)

    path = sys.argv[2]
    cmd = sys.argv[3]
    args = sys.argv[4:]

    try:
        book = RecipeBook(path)
        if cmd == "add":
            if len(args) < 2: raise ValueError("Missing arguments")
            book.add(args[0], int(args[1]))
        elif cmd == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif cmd == "set":
            if len(args) < 2: raise ValueError("Missing arguments")
            book.set_minutes(int(args[0]), int(args[1]))
        elif cmd == "remove":
            if len(args) < 1: raise ValueError("Missing arguments")
            book.remove(int(args[0]))
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
