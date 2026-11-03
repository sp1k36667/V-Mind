import sys
import json
import os

class RecipeBook:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    content = f.read()
                    if not content:
                        raise ValueError("Empty file")
                    self.data = json.loads(content)
                    if "next_id" not in self.data or "items" not in self.data:
                        raise ValueError("Invalid format")
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")

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
        sorted_ids = sorted([int(k) for k in self.data["items"].keys()])
        return [{"id": i, **self.data["items"][str(i)]} for i in sorted_ids]

    def set_minutes(self, id_val, minutes):
        if not isinstance(id_val, int) or str(id_val) not in self.data["items"]:
            raise ValueError("Invalid ID")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        self.data["items"][str(id_val)]["minutes"] = minutes
        self._save()

    def remove(self, id_val):
        if not isinstance(id_val, int) or str(id_val) not in self.data["items"]:
            raise ValueError("Invalid ID")
        del self.data["items"][str(id_val)]
        self._save()

def main():
    args = sys.argv[1:]
    if len(args) < 3 or args[0] != "--file":
        sys.exit(1)
    
    path = args[1]
    cmd = args[2]
    try:
        book = RecipeBook(path)
        if cmd == "add":
            title = args[3]
            minutes = int(args[4])
            book.add(title, minutes)
        elif cmd == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif cmd == "set":
            book.set_minutes(int(args[3]), int(args[4]))
        elif cmd == "remove":
            book.remove(int(args[3]))
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
