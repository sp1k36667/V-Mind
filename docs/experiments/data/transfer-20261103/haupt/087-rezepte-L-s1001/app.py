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
                        raise ValueError("File is empty")
                    self.data = json.loads(content)
                    # Ensure keys are handled correctly
                    self.data["items"] = {int(k): v for k, v in self.data["items"].items()}
            except (json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
                print(f"Error reading file: {e}", file=sys.stderr)
                sys.exit(1)

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError("Title cannot be empty")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be a positive integer")
        
        recipe_id = self.data["next_id"]
        self.data["items"][recipe_id] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self._save()
        return recipe_id

    def list_recipes(self):
        sorted_ids = sorted(self.data["items"].keys())
        result = []
        for rid in sorted_ids:
            item = self.data["items"][rid]
            result.append({"id": rid, "title": item["title"], "minutes": item["minutes"]})
        return result

    def set_minutes(self, rid, minutes):
        if rid not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be a positive integer")
        self.data["items"][rid]["minutes"] = minutes
        self._save()

    def remove(self, rid):
        if rid not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][rid]
        self._save()

def main():
    if len(sys.argv) < 4:
        print("Usage: python3 app.py --file PATH COMMAND [ARGS]", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] != "--file":
        print("Usage: python3 app.py --file PATH COMMAND [ARGS]", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[2]
    command = sys.argv[3]
    args = sys.argv[4:]

    try:
        book = RecipeBook(path)
        if command == "add":
            if len(args) < 2:
                raise ValueError("Missing arguments for add")
            title = " ".join(args[:-1])
            minutes = int(args[-1])
            book.add(title, minutes)
        elif command == "list":
            recipes = book.list_recipes()
            for r in recipes:
                print(f"{r['id']} {r['minutes']} min {r['title']}")
        elif command == "set":
            if len(args) < 2:
                raise ValueError("Missing arguments for set")
            rid = int(args[0])
            minutes = int(args[1])
            book.set_minutes(rid, minutes)
        elif command == "remove":
            if len(args) < 1:
                raise ValueError("Missing argument for remove")
            rid = int(args[0])
            book.remove(rid)
        else:
            print(f"Unknown command: {command}", file=sys.stderr)
            sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
