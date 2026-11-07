import sys
import json
import os

class RecipeBook:
    def __init__(self, path):
        self.path = path
        self.data = None
        self.load()

    def load(self):
        if not os.path.exists(self.path):
            self.data = {"next_id": 1, "items": {}}
            self.save()
            return
        try:
            with open(self.path, 'r') as f:
                data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError
                if not isinstance(data["next_id"], int) or not isinstance(data["items"], dict):
                    raise ValueError
                self.data = data
        except (json.JSONDecodeError, ValueError):
            raise ValueError("Beschädigte Datei")

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_minutes(self, minutes):
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError
        return minutes

    def add(self, title, minutes):
        if not title or not title.strip():
            raise ValueError
        minutes = self._validate_minutes(minutes)
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self.save()
        return new_id

    def list(self):
        res = []
        for i in sorted(self.data["items"].keys()):
            item = self.data["items"][i]
            res.append({"id": i, "title": item["title"], "minutes": item["minutes"]})
        return res

    def set_minutes(self, id_val, minutes):
        if not isinstance(id_val, int) or id_val not in self.data["items"]:
            raise ValueError
        minutes = self._validate_minutes(minutes)
        self.data["items"][id_val]["minutes"] = minutes
        self.save()

    def remove(self, id_val):
        if not isinstance(id_val, int) or id_val not in self.data["items"]:
            raise ValueError
        del self.data["items"][id_val]
        self.save()

def main():
    if len(sys.argv) < 3:
        sys.stderr.write("Fehler: Ungültige Argumente\n")
        sys.exit(1)
    
    path = sys.argv[1]
    cmd = sys.argv[2]
    args = sys.argv[3:]
    
    try:
        book = RecipeBook(path)
        if cmd == "add":
            if len(args) < 2: raise ValueError
            book.add(args[0], int(args[1]))
        elif cmd == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif cmd == "set":
            if len(args) < 2: raise ValueError
            book.set_minutes(int(args[0]), int(args[1]))
        elif cmd == "remove":
            if len(args) < 1: raise ValueError
            book.remove(int(args[0]))
        else:
            raise ValueError
    except (ValueError, IndexError, TypeError, json.JSONDecodeError):
        sys.stderr.write("Error\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
