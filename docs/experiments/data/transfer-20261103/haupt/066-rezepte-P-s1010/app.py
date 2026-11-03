import json
import sys
import argparse
import os

class RecipeBook:
    def __init__(self, path):
        self.path = path
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                        raise ValueError("Invalid format")
                    self.data = data
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError("Title required")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list_items(self):
        items = []
        for key, val in self.data["items"].items():
            items.append({"id": int(key), "title": val["title"], "minutes": val["minutes"]})
        return sorted(items, key=lambda x: x["id"])

    def set_minutes(self, r_id, minutes):
        if str(r_id) not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        self.data["items"][str(r_id)]["minutes"] = minutes
        self._save()

    def remove(self, r_id):
        if str(r_id) not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(r_id)]
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
            if len(args.args) < 2: raise ValueError("Missing args")
            tid = book.add(args.args[0], int(args.args[1]))
            print(tid)
        elif args.command == "list":
            for item in book.list_items():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif args.command == "set":
            if len(args.args) < 2: raise ValueError("Missing args")
            book.set_minutes(int(args.args[0]), int(args.args[1]))
        elif args.command == "remove":
            if len(args.args) < 1: raise ValueError("Missing args")
            book.remove(int(args.args[0]))
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Unexpected error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
