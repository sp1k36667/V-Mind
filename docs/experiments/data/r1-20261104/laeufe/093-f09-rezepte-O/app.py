import sys
import json
import os

class RecipeBook:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    content = json.load(f)
                    if not isinstance(content, dict) or \
                       "next_id" not in content or \
                       not isinstance(content["next_id"], int) or \
                       "items" not in content or \
                       not isinstance(content["items"], dict):
                        raise ValueError
                    self.data = content
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("File is corrupted")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError("Title cannot be empty")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be a positive integer")
        
        recipe_id = self.data["next_id"]
        self.data["items"][str(recipe_id)] = {
            "title": title,
            "minutes": minutes
        }
        self.data["next_id"] += 1
        self._save()
        return recipe_id

    def list(self):
        items = []
        for key, val in self.data["items"].items():
            try:
                rid = int(key)
                items.append({"id": rid, **val})
            except ValueError:
                raise ValueError("Invalid ID")
        return sorted(items, key=lambda x: x["id"])

    def set_minutes(self, recipe_id, minutes):
        rid_str = str(recipe_id)
        if rid_str not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be a positive integer")
        
        self.data["items"][rid_str]["minutes"] = minutes
        self._save()

    def remove(self, recipe_id):
        rid_str = str(recipe_id)
        if rid_str not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][rid_str]
        self._save()

def main():
    try:
        if len(sys.argv) < 3:
            sys.exit(1)
        
        path = sys.argv[1]
        command = sys.argv[2]
        book = RecipeBook(path)

        if command == "add":
            if len(sys.argv) < 5:
                sys.exit(1)
            title = sys.argv[3]
            minutes = int(sys.argv[4])
            book.add(title, minutes)
        elif command == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif command == "set":
            if len(sys.argv) < 5:
                sys.exit(1)
            recipe_id = int(sys.argv[3])
            minutes = int(sys.argv[4])
            book.set_minutes(recipe_id, minutes)
        elif command == "remove":
            if len(sys.argv) < 4:
                sys.exit(1)
            recipe_id = int(sys.argv[3])
            book.remove(recipe_id)
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError, TypeError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
