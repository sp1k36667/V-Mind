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
                    raise ValueError
                self.data = data
                # Ensure keys are treated as integers internally if needed, 
                # but since we use IDs as keys, we just ensure consistency.
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, ValueError):
            if os.path.exists(self.path):
                raise ValueError("Beschädigte Datei")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError("Ungültiger Titel")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minuten müssen > 0 sein")
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted([int(k) for k in self.data["items"].keys()])
        result = []
        for i in sorted_ids:
            item = self.data["items"][str(i)]
            result.append({"id": i, "title": item["title"], "minutes": item["minutes"]})
        return result

    def set_minutes(self, recipe_id, minutes):
        if str(recipe_id) not in self.data["items"]:
            raise ValueError("ID existiert nicht")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minuten müssen > 0 sein")
        self.data["items"][str(recipe_id)]["minutes"] = minutes
        self._save()

    def remove(self, recipe_id):
        if str(recipe_id) not in self.data["items"]:
            raise ValueError("ID existiert nicht")
        del self.data["items"][str(recipe_id)]
        self._save()

import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("command", choices=["add", "list", "set", "remove"])
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()

    try:
        book = RecipeBook(args.file)
        if args.command == "add":
            if len(args.args) < 2: raise ValueError()
            tid = book.add(args.args[0], int(args.args[1]))
            print(tid)
        elif args.command == "list":
            for r in book.list():
                print(f"{r['id']} {r['minutes']} min {r['title']}")
        elif args.command == "set":
            book.set_minutes(int(args.args[0]), int(args.args[1]))
        elif args.command == "remove":
            book.remove(int(args.args[0]))
    except (ValueError, IndexError, TypeError) as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
