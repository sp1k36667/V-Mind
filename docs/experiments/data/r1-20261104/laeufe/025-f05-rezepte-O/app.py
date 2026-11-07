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
                    raise ValueError
                self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self.save()

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError
        recipe_id = self.data["next_id"]
        self.data["items"][recipe_id] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self.save()
        return recipe_id

    def list(self):
        items = []
        for rid, content in self.data["items"].items():
            items.append({"id": int(rid), **content})
        return sorted(items, key=lambda x: x["id"])

    def set_minutes(self, rid, minutes):
        if rid not in self.data["items"] or not isinstance(rid, int):
            raise ValueError
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError
        self.data["items"][rid]["minutes"] = minutes
        self.save()

    def remove(self, rid):
        if rid not in self.data["items"] or not isinstance(rid, int):
            raise ValueError
        del self.data["items"][rid]
        self.save()

def main():
    if len(sys.argv) < 3:
        sys.stderr.write("Usage: python3 app.py --file PATH COMMAND [ARGS]\n")
        sys.exit(1)
    
    if sys.argv[1] != "--file" or len(sys.argv) < 4:
        sys.stderr.write("Usage: python3 app.py --file PATH COMMAND [ARGS]\n")
        sys.exit(1)
        
    path = sys.argv[2]
    try:
        book = RecipeBook(path)
        cmd = sys.argv[3]
        args = sys.argv[4:]

        if cmd == "add":
            if len(args) != 2: raise ValueError
            rid = book.add(args[0], int(args[1]))
            print(rid)
        elif cmd == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif cmd == "set":
            if len(args) != 2: raise ValueError
            book.set_minutes(int(args[0]), int(args[1]))
        elif cmd == "remove":
            if len(args) != 1: raise ValueError
            book.remove(int(args[0]))
        else:
            sys.stderr.write("Unknown command\n")
            sys.exit(1)
    except (ValueError, IndexError, KeyError, TypeError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
