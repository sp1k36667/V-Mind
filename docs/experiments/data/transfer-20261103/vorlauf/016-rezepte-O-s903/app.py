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
                    content = f.read()
                    if not content:
                        raise ValueError("Empty file")
                    self.data = json.load(f)
                    if not isinstance(self.data.get("next_id"), int) or \
                       not isinstance(self.data.get("items"), dict):
                        raise ValueError("Invalid format")
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError("Invalid title")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list_items(self):
        res = []
        for i_id, val in self.data["items"].items():
            res.append({"id": i_id, "title": val["title"], "minutes": val["minutes"]})
        return sorted(res, key=lambda x: x["id"])

    def set_minutes(self, i_id, minutes):
        if i_id not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        self.data["items"][i_id]["minutes"] = minutes
        self._save()

    def remove(self, i_id):
        if i_id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][i_id]
        self._save()

def main():
    args = sys.argv[1:]
    if len(args) < 3:
        return
    
    path = args[0]
    cmd = args[1]
    params = args[2:]

    try:
        book = RecipeBook(path)
        if cmd == "add":
            if len(params) != 2: raise ValueError()
            book.add(params[0], int(params[1]))
        elif cmd == "list":
            for item in book.list_items():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif cmd == "set":
            if len(params) != 2: raise ValueError()
            book.set_minutes(int(params[0]), int(params[1]))
        elif cmd == "remove":
            if len(params) != 1: raise ValueError()
            book.remove(int(params[0]))
        else:
            raise ValueError()
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
