import json
import sys
import argparse
import os

class RecipeBook:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    content = f.read()
                    if not content.strip():
                        raise ValueError("Empty file")
                    self.data = json.loads(content)
                    if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                        raise ValueError("Invalid format")
                    if not isinstance(self.data["next_id"], int):
                        raise ValueError("Invalid next_id")
                    # Ensure keys are handled as strings internally to match JSON
                    self.data["items"] = self.data["items"]
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError("Title cannot be empty")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {
            "title": title,
            "minutes": minutes
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        items = []
        for k, v in self.data["items"].items():
            items.append({"id": int(k), **v})
        return sorted(items, key=lambda x: x["id"])

    def set_minutes(self, id_str, minutes):
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        self.data["items"][id_str]["minutes"] = minutes
        self._save()

    def remove(self, id_str):
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id_str]
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
            book.add(title, minutes)
        elif args.command == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif args.command == "set":
            if len(args.args) < 2:
                raise ValueError("Missing arguments")
            book.set_minutes(args.args[0], int(args.args[1]))
        elif args.command == "remove":
            if len(args.args) < 1:
                raise ValueError("Missing arguments")
            book.remove(args.args[0])
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Unexpected error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
