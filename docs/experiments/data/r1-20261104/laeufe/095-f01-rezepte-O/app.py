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
                if not isinstance(data["next_id"], int) or not isinstance(data["items"], dict):
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
        self.data["items"][new_id] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        res = []
        for idx in sorted(self.data["items"].keys()):
            val = self.data["items"][idx]
            res.append({"id": idx, "title": val["title"], "minutes": val["minutes"]})
        return res

    def set_minutes(self, r_id, minutes):
        if r_id not in self.data["items"] or not isinstance(r_id, int):
            raise ValueError("Not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        self.data["items"][r_id]["minutes"] = minutes
        self._save()

    def remove(self, r_id):
        if r_id not in self.data["items"] or not isinstance(r_id, int):
            raise ValueError("Not found")
        del self.data["items"][r_id]
        self._save()

def main():
    if len(sys.argv) < 4:
        sys.stderr.write("Usage: python3 app.py --file DATEI BEFEHL [ARGUMENTE]\n")
        sys.exit(1)
    
    if sys.argv[1] != "--file":
        sys.exit(1)

    path = sys.argv[2]
    cmd = sys.argv[3]
    params = sys.argv[4:]
    
    try:
        book = RecipeBook(path)
        if cmd == "add":
            if len(params) < 2: raise ValueError("Missing arguments")
            tid = book.add(params[0], int(params[1]))
            print(tid)
        elif cmd == "list":
            for r in book.list():
                print(f"{r['id']} {r['minutes']} min {r['title']}")
        elif cmd == "set":
            if len(params) < 2: raise ValueError("Missing arguments")
            book.set_minutes(int(params[0]), int(params[1]))
        elif cmd == "remove":
            if len(params) < 1: raise ValueError("Missing arguments")
            book.remove(int(params[0]))
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError, TypeError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
