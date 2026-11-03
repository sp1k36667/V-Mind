import json
import sys
import argparse
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
                raise ValueError("Damaged file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_minutes(self, minutes):
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be positive integer")

    def add(self, title, minutes):
        if not title or not title.strip():
            raise ValueError("Title cannot be empty")
        self._validate_minutes(minutes)
        
        recipe_id = self.data["next_id"]
        self.data["items"][str(recipe_id)] = {
            "title": title,
            "minutes": minutes
        }
        self.data["next_id"] += 1
        self._save()
        return recipe_id

    def list_recipes(self):
        items = []
        for key, val in self.data["items"].items():
            items.append({
                "id": int(key),
                "title": val["title"],
                "minutes": val["minutes"]
            })
        return sorted(items, key=lambda x: x["id"])

    def set_minutes(self, recipe_id, minutes):
        key = str(recipe_id)
        if key not in self.data["items"]:
            raise ValueError("ID not found")
        self._validate_minutes(minutes)
        self.data["items"][key]["minutes"] = minutes
        self._save()

    def remove(self, recipe_id):
        key = str(recipe_id)
        if key not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][key]
        self._save()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("command", choices=["add", "list", "set", "remove"])
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()

    try:
        book = RecipeBook(args.file)
        if args.command == "add":
            if len(args.args) < 2:
                raise ValueError("Missing arguments")
            title = args.args[0]
            minutes = int(args.args[1])
            rid = book.add(title, minutes)
            print(rid)
        elif args.command == "list":
            recipes = book.list_recipes()
            for r in recipes:
                print(f"{r['id']} {r['minutes']} min {r['title']}")
        elif args.command == "set":
            if len(args.args) < 2:
                raise ValueError("Missing arguments")
            rid = int(args.args[0])
            minutes = int(args.args[1])
            book.set_minutes(rid, minutes)
        elif args.command == "remove":
            if len(args.args) < 1:
                raise ValueError("Missing arguments")
            rid = int(args.args[0])
            book.remove(rid)
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
