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
                    data = json.load(f)
                if not isinstance(data, dict) or "items" not in data or not isinstance(data["items"], dict):
                    raise ValueError("Invalid format")
                self.data = data
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
        if current is None or current < qty:
            raise ValueError("Not enough stock")
        
        new_qty = current - qty
        if new_qty == 0:
            del self.data["items"][name]
        else:
            self.data["items"][name] = new_qty
        self._save()

    def list(self):
        items = []
        for name, qty in self.data["items"].items():
            items.append({"name": name, "qty": qty})
        return sorted(items, key=lambda x: x["name"])

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 2:
            sys.exit(1)
        
        path = args[0]
        command = args[1]
        params = args[2:]
        
        pantry = Pantry(path)
        
        if command == "add":
            if len(params) != 2: raise ValueError("Missing args")
            pantry.add(params[0], int(params[1]))
        elif command == "take":
            if len(params) != 2: raise ValueError("Missing args")
            pantry.take(params[0], int(params[1]))
        elif command == "list":
            for item in pantry.list():
                print(f"{item['qty']} {item['name']}")
        else:
            sys.exit(1)
            
    except (ValueError, IndexError, KeyError, TypeError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
