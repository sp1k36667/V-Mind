import sys
import json
import os

class Pantry:
    def __init__(self, path):
        self.path = path
        self.data = {"items": {}}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    self.data = json.load(f)
                if not isinstance(self.data, dict) or "items" not in self.data:
                    raise ValueError("Invalid format")
                if not isinstance(self.data["items"], dict):
                    raise ValueError("Invalid format")
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, name, qty):
        if not name or name.isspace():
            raise ValueError("Invalid name")
        name = name.strip()
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Invalid quantity")
        
        current = self.data["items"].get(name, 0)
        self.data["items"][name] = current + qty
        self._save()

    def take(self, name, qty):
        if not name or name.isspace():
            raise ValueError("Invalid name")
        name = name.strip()
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Invalid quantity")
        
        current = self.data["items"].get(name)
        if current is None:
            raise ValueError("Not found")
        if current < qty:
            raise ValueError("Not enough")
        
        new_qty = current - qty
        if new_qty == 0:
            del self.data["items"][name]
        else:
            self.data["items"][name] = new_qty
        self._save()

    def list_items(self):
        items = []
        for name, qty in self.data["items"].items():
            items.append({"name": name, "qty": qty})
        return sorted(items, key=lambda x: x["name"])

def main():
    if len(sys.argv) < 4:
        sys.stderr.write("Usage: python3 app.py --file PATH COMMAND [ARGS]\n")
        sys.exit(1)
    
    if sys.argv[1] != "--file":
        sys.stderr.write("Usage: python3 app.py --file PATH COMMAND [ARGS]\n")
        sys.exit(1)

    path = sys.argv[2]
    cmd = sys.argv[3]
    args = sys.argv[4:]

    try:
        pantry = Pantry(path)
        if cmd == "add" and len(args) == 2:
            pantry.add(args[0], int(args[1]))
        elif cmd == "take" and len(args) == 2:
            pantry.take(args[0], int(args[1]))
        elif cmd == "list":
            for item in pantry.list_items():
                print(f"{item['qty']} {item['name']}")
        else:
            sys.stderr.write("Unknown command or arguments\n")
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Unexpected error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
