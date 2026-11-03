import json
import sys
import argparse

class RecipeBook:
    def __init__(self, path):
        self.path = path
        try:
            with open(self.path, 'r') as f:
                data = json.load(f)
                if "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.next_id = data["next_id"]
                self.items = data["items"]
        except FileNotFoundError:
            self.next_id = 1
            self.items = {}
        except (json.JSONDecodeError, ValueError):
            raise ValueError("Damaged or invalid JSON file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump({"next_id": self.next_id, "items": self.items}, f)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError("Title cannot be empty")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be a positive integer")
        
        id_ = self.next_id
        self.items[str(id_)] = {"title": title, "minutes": minutes}
        self.next_id += 1
        self._save()
        return id_

    def list_recipes(self):
        sorted_ids = sorted([int(k) for k in self.items.keys()])
        result = []
        for i in sorted_ids:
            item = self.items[str(i)]
            result.append({"id": i, "title": item["title"], "minutes": item["minutes"]})
        return result

    def set_minutes(self, id_str, minutes):
        if id_str not in self.items:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be a positive integer")
        self.items[id_str]["minutes"] = minutes
        self._save()

    def remove(self, id_str):
        if id_str not in self.items:
            raise ValueError("ID not found")
        del self.items[id_str]
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
            title = args.args[0]
            minutes = int(args.args[1])
            book.add(title, minutes)
        elif args.command == "list":
            for r in book.list_recipes():
                print(f"{r['id']} {r['minutes']} min {r['title']}")
        elif args.command == "set":
            if len(args.args) < 2: raise ValueError("Missing args")
            book.set_minutes(args.args[0], int(args.args[1]))
        elif args.command == "remove":
            if len(args.args) < 1: raise ValueError("Missing args")
            book.remove(args.args[0])
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Unexpected error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
