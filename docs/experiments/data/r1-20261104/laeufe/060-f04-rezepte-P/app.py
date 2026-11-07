import sys
import json
import os

class RecipeBook:
    def __init__(self, path):
        self.path = path
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                if not isinstance(data["next_id"], int) or not isinstance(data["items"], dict):
                    raise ValueError("Invalid format")
                self.data = data
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError("Empty title")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        items = []
        for key, val in self.data["items"].items():
            items.append({"id": int(key), "title": val["title"], "minutes": val["minutes"]})
        return sorted(items, key=lambda x: x["id"])

    def set_minutes(self, id_val, minutes):
        s_id = str(id_val)
        if s_id not in self.data["items"]:
            raise ValueError("Unknown ID")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        self.data["items"][s_id]["minutes"] = minutes
        self._save()

    def remove(self, id_val):
        s_id = str(id_val)
        if s_id not in self.data["items"]:
            raise ValueError("Unknown ID")
        del self.data["items"][s_id]
        self._save()

def main():
    if len(sys.argv) < 4 or sys.argv[1] != "--file":
        sys.exit(1)
    
    path = sys.argv[2]
    cmd = sys.argv[3]
    args = sys.argv[4:]

    try:
        book = RecipeBook(path)
        if cmd == "add":
            if len(args) < 2: raise ValueError()
            book.add(args[0], int(args[1]))
        elif cmd == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif cmd == "set":
            if len(args) < 2: raise ValueError()
            book.set_minutes(int(args[0]), int(args[1]))
        elif cmd == "remove":
            if len(args) < 1: raise ValueError()
            book.remove(int(args[0]))
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
