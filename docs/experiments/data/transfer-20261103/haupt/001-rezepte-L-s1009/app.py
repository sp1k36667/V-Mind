import sys
import json
import os

class RecipeBook:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if not isinstance(loaded, dict) or "next_id" not in loaded or "items" not in loaded:
                        raise ValueError("Invalid format")
                    self.data = loaded
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
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
        sorted_ids = sorted(self.data["items"].keys(), key=int)
        result = []
        for key in sorted_ids:
            item = self.data["items"][key]
            result.append({"id": int(key), "title": item["title"], "minutes": item["minutes"]})
        return result

    def set_minutes(self, id_str, minutes):
        if not str(id_str).isdigit() or int(id_str) <= 0:
            raise ValueError("Invalid ID")
        if str(id_str) not in self.data["items"]:
            raise ValueError("Not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        
        self.data["items"][str(id_str)]["minutes"] = minutes
        self._save()

    def remove(self, id_str):
        if not str(id_str).isdigit() or int(id_str) <= 0:
            raise ValueError("Invalid ID")
        if str(id_str) not in self.data["items"]:
            raise ValueError("Not found")
        
        del self.data["items"][str(id_str)]
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
            rid = book.add(args[0], int(args[1]))
            print(rid)
        elif cmd == "list":
            for r in book.list():
                print(f"{r['id']} {r['minutes']} min {r['title']}")
        elif cmd == "set":
            book.set_minutes(args[0], int(args[1]))
        elif cmd == "remove":
            book.remove(args[0])
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
