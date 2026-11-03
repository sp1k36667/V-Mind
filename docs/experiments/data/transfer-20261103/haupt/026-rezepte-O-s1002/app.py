import sys
import json
import os

class RecipeBook:
    def __init__(self, path):
        self.path = path
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
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
            raise ValueError("Empty title")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self.save()
        return new_id

    def list(self):
        items = []
        for id, content in self.data["items"].items():
            items.append({"id": id, "title": content["title"], "minutes": content["minutes"]})
        return sorted(items, key=lambda x: x["id"])

    def set_minutes(self, id, minutes):
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        self.data["items"][id]["minutes"] = minutes
        self.save()

    def remove(self, id):
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id]
        self.save()

def main():
    if len(sys.argv) < 3:
        sys.exit(1)
    
    path = sys.argv[1]
    try:
        book = RecipeBook(path)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

    cmd = sys.argv[2]
    args = sys.argv[3:]

    try:
        if cmd == "add":
            if len(args) < 2: raise ValueError("Missing args")
            book.add(args[0], int(args[1]))
        elif cmd == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif cmd == "set":
            if len(args) < 2: raise ValueError("Missing args")
            book.set_minutes(int(args[0]), int(args[1]))
        elif cmd == "remove":
            if len(args) < 1: raise ValueError("Missing args")
            book.remove(int(args[0]))
        else:
            sys.exit(1)
    except (ValueError, IndexError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
