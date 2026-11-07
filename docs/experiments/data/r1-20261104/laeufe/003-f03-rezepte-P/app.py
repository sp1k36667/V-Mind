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
                    raise ValueError
                self.data = data
        except FileNotFoundError:
            self.data = {"next_id": 1, "items": {}}
            self.save()
        except (json.JSONDecodeError, ValueError):
            # If file exists but is corrupt/invalid, raise ValueError
            # unless it doesn't exist at all.
            # The prompt says: "A pre-existing corrupted JSON file triggers a ValueError"
            # and "The file does not exist initially."
            # So we check if file exists first.
            import os
            if os.path.exists(self.path):
                raise ValueError
            self.data = {"next_id": 1, "items": {}}
            self.save()

    def save(self):
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
        self.save()
        return new_id

    def list(self):
        items = []
        for r_id in sorted(self.data["items"].keys()):
            item = self.data["items"][r_id]
            items.append({"id": r_id, "title": item["title"], "minutes": item["minutes"]})
        return items

    def set_minutes(self, r_id, minutes):
        if r_id not in self.data["items"]:
            raise ValueError
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError
        self.data["items"][r_id]["minutes"] = minutes
        self.save()

    def remove(self, r_id):
        if r_id not in self.data["items"]:
            raise ValueError
        del self.data["items"][r_id]
        self.save()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("command", choices=["add", "list", "set", "remove"])
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()

    try:
        book = RecipeBook(args.file)
        if args.command == "add":
            if len(args.args) != 2: raise ValueError
            title = args.args[0]
            try:
                minutes = int(args.args[1])
            except ValueError:
                raise ValueError
            rid = book.add(title, minutes)
            print(rid)
        elif args.command == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif args.command == "set":
            if len(args.args) != 2: raise ValueError
            try:
                rid = int(args.args[0])
                minutes = int(args.args[1])
            except ValueError:
                raise ValueError
            book.set_minutes(rid, minutes)
        elif args.command == "remove":
            if len(args.args) != 1: raise ValueError
            try:
                rid = int(args.args[0])
            except ValueError:
                raise ValueError
            book.remove(rid)
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
