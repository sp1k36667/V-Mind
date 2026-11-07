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
                    content = f.read()
                    if not content:
                        raise ValueError("Empty file")
                    loaded = json.load(f)
                    if not isinstance(loaded, dict) or "next_id" not in loaded or "items" not in loaded:
                        raise ValueError("Invalid format")
                    if not isinstance(loaded["next_id"], int) or not isinstance(loaded["items"], dict):
                        raise ValueError("Invalid format")
                    self.data = loaded
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file")

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
    try:
        if len(sys.argv) < 3:
            sys.exit(1)
        path = sys.argv[1]
        cmd = sys.argv[2]
        args = sys.argv[3:]
        
        book = RecipeBook(path)
        
        if cmd == "add":
            if len(args) != 2:
                raise ValueError("Usage: add TITLE MINUTES")
            book.add(args[0], int(args[1]))
        elif cmd == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif cmd == "set":
            if len(args) != 2:
                raise ValueError("Usage: set ID MINUTES")
            book.set_minutes(int(args[0]), int(args[1]))
        elif cmd == "remove":
            if len(args) != 1:
                raise ValueError("Usage: remove ID")
            book.remove(int(args[0]))
        else:
            sys.stderr.write("Unknown command\n")
            sys.exit(1)
            
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
