import json
import sys
import argparse
import os

class RecipeBook:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    loaded = json.load(f)
                if not isinstance(loaded, dict) or "next_id" not in loaded or "items" not in loaded:
                    raise ValueError
                self.data = loaded
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("File corrupted")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys())
        result = []
        for i in sorted_ids:
            item = self.data["items"][i]
            result.append({"id": i, "title": item["title"], "minutes": item["minutes"]})
        return result

    def set_minutes(self, recipe_id, minutes):
        if recipe_id not in self.data["items"] or not isinstance(recipe_id, int):
            raise ValueError
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError
        self.data["items"][recipe_id]["minutes"] = minutes
        self._save()

    def remove(self, recipe_id):
        if recipe_id not in self.data["items"] or not isinstance(recipe_id, int):
            raise ValueError
        del self.data["items"][recipe_id]
        self._save()

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--file", required=True)
    parser.add_argument("command", nargs=1)
    parser.add_argument("args", nargs="*")
    
    try:
        args = parser.parse_args()
        book = RecipeBook(args.file)
        cmd = args.command[0]

        if cmd == "add":
            if len(args) < 2: raise ValueError
            book.add(args[0], int(args[1]))
        elif cmd == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif cmd == "set":
            if len(args) < 2: raise ValueError
            book.set_minutes(int(args[0]), int(args[1]))
        elif cmd == "remove":
            if len(args) < 1: raise ValueError
            book.remove(int(args[0]))
        else:
            pass
    except (ValueError, IndexError, KeyError, TypeError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
