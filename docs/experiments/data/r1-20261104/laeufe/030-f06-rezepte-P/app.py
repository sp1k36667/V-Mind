import json
import sys
import argparse

class RecipeBook:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        self._load()

    def _load(self):
        try:
            with open(self.path, 'r') as f:
                data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                if not isinstance(data["next_id"], int) or not isinstance(data["items"], dict):
                    raise ValueError("Invalid types")
                self.data = data
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, ValueError):
            raise ValueError("Damaged file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError("Empty title")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"title": str(title), "minutes": int(minutes)}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys())
        result = []
        for i in sorted_ids:
            item = self.data["items"][i]
            result.append({"id": int(i), "title": str(item["title"]), "minutes": int(item["minutes"])})
        return result

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("command", choices=["add", "list", "set", "remove"])
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()

    try:
        book = RecipeBook(args.file)
        if args.command == "add":
            if len(args.args) != 2: raise ValueError("Need title and minutes")
            book.add(args.args[0], int(args.args[1]))
        elif args.command == "list":
            for r in book.list():
                print(f"{r['id']} {r['minutes']} min {r['title']}")
        elif args.command == "set":
            if len(args.args) != 2: raise ValueError("Need ID and minutes")
            book.set_minutes(int(args.args[0]), int(args.args[1]))
        elif args.command == "remove":
            if len(args.args) != 1: raise ValueError("Need ID")
            book.remove(int(args.args[0]))
    except (ValueError, IndexError, KeyError, TypeError) as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
