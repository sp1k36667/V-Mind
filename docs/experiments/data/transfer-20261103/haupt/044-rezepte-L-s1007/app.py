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
                    self.data = json.load(f)
                if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                    raise ValueError("Invalid format")
            except (json.JSONDecodeError, ValueError):
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
        items = []
        for k, v in self.data["items"].items():
            items.append({"id": int(k), "title": v["title"], "minutes": v["minutes"]})
        return sorted(items, key=lambda x: x["id"])

    def set_minutes(self, id_val, minutes):
        if not isinstance(id_val, int) or str(id_val) not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        self.data["items"][str(id_val)]["minutes"] = minutes
        self._save()

    def remove(self, id_val):
        if not isinstance(id_val, int) or str(id_val) not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(id_val)]
        self._save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 2:
            sys.exit(1)
        
        path = args[0]
        cmd = args[1]
        book = RecipeBook(path)

        if cmd == "add" and len(args) == 3:
            title = args[2]
            minutes = int(args[3]) if len(args) > 3 else 0 # Adjusted for CLI logic
            # Re-parsing CLI args for correct mapping
            title = args[2]
            minutes = int(args[3])
            book.add(title, minutes)
        elif cmd == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif cmd == "set" and len(args) == 4:
            book.set_minutes(int(args[2]), int(args[3]))
        elif cmd == "remove" and len(args) == 3:
            book.remove(int(args[2]))
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    # Fix for CLI argument handling based on prompt: --file DATEI BEFEHL [ARGUMENTE]
    # The prompt says: python3 app.py --file DATEI BEFEHL [ARGUMENTE]
    # Let's adjust the parsing to match exactly that.
    try:
        if len(sys.argv) < 4 or sys.argv[1] != "--file":
            sys.exit(1)
        
        path = sys.argv[2]
        cmd = sys.argv[3]
        book = RecipeBook(path)
        
        if cmd == "add":
            title = sys.argv[4]
            minutes = int(sys.argv[5])
            book.add(title, minutes)
        elif cmd == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif cmd == "set":
            book.set_minutes(int(sys.argv[4]), int(sys.argv[5]))
        elif cmd == "remove":
            book.remove(int(sys.argv[4]))
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
```

Wait, I need to rewrite it to be cleaner and strictly follow the prompt's CLI and logic.

```python
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
                    loaded = json.load(f)
                    if not isinstance(loaded, dict) or "next_id" not in loaded or "items" not in loaded:
                        raise ValueError
                    self.data = loaded
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Invalid or corrupted file")

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
        items = []
        for k, v in self.data["items"].items():
            items.append({"id": int(k), "title": v["title"], "minutes": v["minutes"]})
        return sorted(items, key=lambda x: x["id"])

    def set_minutes(self, id_val, minutes):
        if not isinstance(id_val, int) or str(id_val) not in self.data["items"]:
            raise ValueError("Invalid ID")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Minutes must be > 0")
        self.data["items"][str(id_val)]["minutes"] = minutes
        self._save()

    def remove(self, id_val):
        if not isinstance(id_val, int) or str(id_val) not in self.data["items"]:
            raise ValueError("Invalid ID")
        del self.data["items"][str(id_val)]
        self._save()

if __name__ == "__main__":
    try:
        if len(sys.argv) < 4 or sys.argv[1] != "--file":
            sys.exit(1)
        path = sys.argv[2]
        cmd = sys.argv[3]
        book = RecipeBook(path)
        
        if cmd == "add" and len(sys.argv) == 6:
            book.add(sys.argv[4], int(sys.argv[5]))
        elif cmd == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif cmd == "set" and len(sys.argv) == 6:
            book.set_minutes(int(sys.argv[4]), int(sys.argv[5]))
        elif cmd == "remove" and len(sys.argv) == 5:
            book.remove(int(sys.argv[4]))
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
```
