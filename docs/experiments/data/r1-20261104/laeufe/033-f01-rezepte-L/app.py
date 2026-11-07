import json
import sys
import os

class RecipeBook:
    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, minutes):
        if not title or not title.strip():
            raise ValueError("Title empty")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        
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

    def set_minutes(self, r_id, minutes):
        r_id_str = str(r_id)
        if r_id_str not in self.data["items"]:
            raise ValueError("Not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        self.data["items"][r_id_str]["minutes"] = minutes
        self._save()

    def remove(self, r_id):
        r_id_str = str(r_id)
        if r_id_str not in self.data["items"]:
            raise ValueError("Not found")
        del self.data["items"][r_id_str]
        self._save()

def main():
    args = sys.argv[1:]
    if len(args) < 3:
        sys.exit(1)
    
    path = args[0]
    cmd = args[1]
    params = args[2:]
    
    try:
        book = RecipeBook(path)
        if cmd == "add":
            if len(params) < 2: raise ValueError()
            tid = book.add(params[0], int(params[1]))
            print(tid)
        elif cmd == "list":
            for r in book.list():
                print(f"{r['id']} {r['minutes']} min {r['title']}")
        elif cmd == "set":
            if len(params) < 2: raise ValueError()
            book.set_minutes(int(params[0]), int(params[1]))
        elif cmd == "remove":
            if len(params) < 1: raise ValueError()
            book.remove(int(params[0]))
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError):
        sys.stderr.write("Error\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
