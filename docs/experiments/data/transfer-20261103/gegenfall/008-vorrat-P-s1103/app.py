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
                if not isinstance(self.data, dict) or "items" not in self.data or not isinstance(self.data["items"], dict):
                    raise ValueError("Invalid format")
            except (json.JSONDecodeError, ValueError, KeyError):
                raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, name, qty):
        name = name.strip()
        if not name:
            raise ValueError("Empty name")
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Invalid quantity")
        
        current = self.data["items"].get(name, 0)
        self.data["items"][name] = current + qty
        self._save()

    def take(self, name, qty):
        name = name.strip()
        if not name:
            raise ValueError("Empty name")
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Invalid quantity")
        
        current = self.data["items"].get(name)
        if current is None or current < qty:
            raise ValueError("Insufficient quantity or unknown name")
        
        new_qty = current - qty
        if new_qty == 0:
            del self.data["items"][name]
        else:
            self.data["items"][name] = new_qty
        self._save()

    def list_items(self):
        res = []
        for name, qty in sorted(self.data["items"].items()):
            res.append({"name": name, "qty": qty})
        return res

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        
        path = args[0]
        cmd = args[1]
        params = args[2:]
        
        pantry = Pantry(path)
        
        if cmd == "add":
            if len(params) != 2: raise ValueError()
            pantry.add(params[0], int(params[1]))
        elif cmd == "take":
            if len(params) != 2: raise ValueError()
            pantry.take(params[0], int(params[1]))
        elif cmd == "list":
            for item in pantry.list_items():
                print(f"{item['qty']} {item['name']}")
        else:
            sys.exit(1)
            
    except (ValueError, IndexError, TypeError) as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
