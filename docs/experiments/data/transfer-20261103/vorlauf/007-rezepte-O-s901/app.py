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
                    self.data = json.load(f)
                    if not isinstance(self.data.get("next_id"), int) or \
                       not isinstance(self.data.get("items"), dict):
                        raise ValueError
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
            items.append({"id": int(key), **val})
        return sorted(items, key=lambda x: x["id"])

    def set_minutes(self, recipe_id, minutes):
        if str(recipe_id) not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be a positive integer")
        
        self.data["items"][str(recipe_id)]["minutes"] = minutes
        self._save()

    def remove(self, recipe_id):
        if str(recipe_id) not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(recipe_id)]
        self._save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        
        path = args[0]
        command = args[1]
        book = RecipeBook(path)

        if command == "add":
            title = args[2]
            minutes = int(args[3])
            book.add(title, minutes)
        elif command == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif command == "set":
            recipe_id = int(args[2])
            minutes = int(args[3])
            book.set_minutes(recipe_id, minutes)
        elif command == "remove":
            recipe_id = int(args[2])
            book.remove(recipe_id)
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
