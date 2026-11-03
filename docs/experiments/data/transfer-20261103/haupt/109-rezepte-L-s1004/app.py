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
                if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                    raise ValueError("Invalid format")
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

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

    def list(self):
        res = []
        for k, v in self.data["items"].items():
            res.append({"id": int(k), "title": v["title"], "minutes": v["minutes"]})
        return sorted(res, key=lambda x: x["id"])

    def set_minutes(self, id_str, minutes):
        if not str(id_str).isdigit():
            raise ValueError("Invalid ID")
        id_int = int(id_str)
        if str(id_int) not in self.data["items"]:
            raise ValueError("Not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        
        self.data["items"][str(id_int)]["minutes"] = minutes
        self._save()

    def remove(self, id_str):
        if not str(id_str).isdigit():
            raise ValueError("Invalid ID")
        id_int = int(id_str)
        if str(id_int) not in self.data["items"]:
            raise ValueError("Not found")
        
        del self.data["items"][str(id_int)]
        self._save()

def main():
    if len(sys.argv) < 4:
        sys.exit(1)
    
    path = sys.argv[1]
    cmd = sys.argv[2]
    args = sys.argv[3:]

    try:
        book = RecipeBook(path)
        if cmd == "add":
            if len(args) < 2: raise ValueError()
            id_res = book.add(args[0], int(args[1]))
            print(id_res)
        elif cmd == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif cmd == "set":
            if len(args) < 2: raise ValueError()
            book.set_minutes(args[0], int(args[1]))
        elif cmd == "remove":
            if len(args) < 1: raise ValueError()
            book.remove(args[0])
        else:
            pass
    except Exception as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
