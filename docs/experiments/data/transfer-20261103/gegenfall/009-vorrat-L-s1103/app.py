import sys
import json
import os

class Pantry:
    def __init__(self, path):
        self.path = path
        self.data = {"items": {}}
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    loaded = json.load(f)
                    if not isinstance(loaded, dict) or "items" not in loaded:
                        raise ValueError("Invalid format")
                    self.data = loaded
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, name, qty):
        if not name or name.isspace():
            raise ValueError("Empty name")
        name = name.strip()
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Invalid quantity")
        
        current = self.data["items"].get(name, 0)
        self.data["items"][name] = current + qty
        self._save()

    def take(self, name, qty):
        if not name or name.isspace():
            raise ValueError("Empty name")
        name = name.strip()
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Invalid quantity")
        
        current = self.data["items"].get(name)
        if current is None:
            raise ValueError("Unknown item")
        if current < qty:
            raise ValueError("Not enough quantity")
        
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
    args = sys.argv[1:]
    if len(args) < 3:
        sys.stderr.write("Usage: python3 app.py --file PATH COMMAND [ARGS]\n")
        sys.exit(1)
    
    if args[0] != "--file":
        sys.stderr.write("Expected --file\n")
        sys.exit(1)
        
    path = args[1]
    cmd = args[2]
    params = args[3:]

    try:
        pantry = Pantry(path)
        if cmd == "add":
            if len(params) != 2:
                raise ValueError("add requires NAME and MENGE")
            pantry.add(params[0], int(params[1]))
        elif cmd == "take":
            if len(params) != 2:
                raise ValueError("take requires NAME and MENGE")
            pantry.take(params[0], int(params[1]))
        elif cmd == "list":
            for item in pantry.list_items():
                print(f"MENGE {item['qty']} {item['name']}")
        else:
            sys.stderr.write("Unknown command\n")
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Unexpected error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
