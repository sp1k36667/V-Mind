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
                    raise ValueError("Invalid format")
                self.data = data
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, ValueError, TypeError):
            raise ValueError("File is corrupted")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError("Title cannot be empty")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        
        id_val = self.data["next_id"]
        self.data["items"][id_val] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self._save()
        return id_val

    def list(self):
        res = []
        for id_val, content in self.data["items"].items():
            if not isinstance(id_val, int):
                raise ValueError("ID must be int")
            res.append({"id": id_val, "title": content["title"], "minutes": content["minutes"]})
        return sorted(res, key=lambda x: x["id"])

    def set_minutes(self, id_val, minutes):
        if id_val not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        self.data["items"][id_val]["minutes"] = minutes
        self._save()

    def remove(self, id_val):
        if id_val not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id_val]
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
            print(book.add(title, minutes))
        elif args.command == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif args.command == "set":
            if len(args.args) < 2:
                raise ValueError("Missing arguments")
            id_val = int(args.args[0])
            minutes = int(args.args[1])
            book.set_minutes(id_val, minutes)
        elif args.command == "remove":
            if len(args.args) < 1:
                raise ValueError("Missing arguments")
            id_val = int(args.args[0])
            book.remove(id_val)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
