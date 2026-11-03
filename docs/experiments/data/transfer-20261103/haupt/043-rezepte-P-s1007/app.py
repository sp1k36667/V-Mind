import sys
import json
import os

class RecipeBook:
    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self.save()

    def save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError("Empty title")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        
        recipe_id = self.data["next_id"]
        self.data["items"][recipe_id] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self.save()
        return recipe_id

    def list_recipes(self):
        sorted_ids = sorted(self.data["items"].keys())
        result = []
        for rid in sorted_ids:
            item = self.data["items"][rid]
            result.append({"id": rid, "title": item["title"], "minutes": item["minutes"]})
        return result

    def set_minutes(self, rid, minutes):
        if rid not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        self.data["items"][rid]["minutes"] = minutes
        self.save()

    def remove(self, rid):
        if rid not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][rid]
        self.save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 2:
            return
        
        file_path = args[0]
        command = args[1]
        book = RecipeBook(file_path)

        if command == "add":
            if len(args) < 4: raise ValueError("Missing args")
            rid = book.add(args[2], int(args[3]))
            print(rid)
        elif command == "list":
            recipes = book.list_recipes()
            for r in recipes:
                print(f"{r['id']} {r['minutes']} min {r['title']}")
        elif command == "set":
            if len(args) < 4: raise ValueError("Missing args")
            book.set_minutes(int(args[2]), int(args[3]))
        elif command == "remove":
            if len(args) < 3: raise ValueError("Missing args")
            book.remove(int(args[2]))
        else:
            raise ValueError("Unknown command")
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
