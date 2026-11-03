import json
import sys
import argparse

class RecipeBook:
    def __init__(self, path):
        self.path = path
        self.data = self._load()

    def _load(self):
        try:
            with open(self.path, 'r') as f:
                data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError
                return data
        except FileNotFoundError:
            return {"next_id": 1, "items": {}}
        except (json.JSONDecodeError, ValueError):
            raise ValueError(f"File {self.path} is corrupted.")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError("Title cannot be empty.")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be a positive integer.")
        
        recipe_id = self.data["next_id"]
        self.data["items"][recipe_id] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self._save()
        return recipe_id

    def list_recipes(self):
        sorted_ids = sorted(self.data["items"].keys())
        results = []
        for rid in sorted_ids:
            item = self.data["items"][rid]
            results.append({"id": rid, "title": item["title"], "minutes": item["minutes"]})
        return results

    def set_minutes(self, recipe_id, minutes):
        if recipe_id not in self.data["items"]:
            raise ValueError(f"ID {recipe_id} not found.")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be a positive integer.")
        self.data["items"][recipe_id]["minutes"] = minutes
        self._save()

    def remove(self, recipe_id):
        if recipe_id not in self.data["items"]:
            raise ValueError(f"ID {recipe_id} not found.")
        del self.data["items"][recipe_id]
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
            if len(args.args) < 2: raise ValueError("Need title and minutes")
            rid = book.add(args.args[0], int(args.args[1]))
            print(rid)
        elif args.command == "list":
            for r in book.list_recipes():
                print(f"{r['id']} {r['minutes']} min {r['title']}")
        elif args.command == "set":
            if len(args.args) < 2: raise ValueError("Need ID and minutes")
            book.set_minutes(int(args.args[0]), int(args.args[1]))
        elif args.command == "remove":
            if len(args.args) < 1: raise ValueError("Need ID")
            book.remove(int(args.args[0]))
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
