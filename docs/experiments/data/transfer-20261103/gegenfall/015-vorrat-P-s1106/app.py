import json
import sys
import os

class Pantry:
    def __init__(self, path):
        self.path = path
        self.data = {"items": {}}
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    self.data = json.load(f)
                    if not isinstance(self.data, dict) or "items" not in self.data:
                        raise ValueError("Invalid format")
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged file")

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
        
        if name not in self.data["items"]:
            raise ValueError("Unknown item")
        
        current = self.data["items"][name]
        if current < qty:
            raise ValueError("Insufficient quantity")
        
        new_qty = current - qty
        if new_qty == 0:
            del self.data["items"][name]
        else:
            self.data["items"][name] = new_qty
        self._save()

    def list_items(self):
        result = []
        for name, qty in self.data["items"].items():
            result.append({"name": name, "qty": qty})
        return sorted(result, key=lambda x: x["name"])

def main():
    if len(sys.argv) < 4 or sys.argv[1] != "--file":
        sys.exit(1)
    
    path = sys.argv[2]
    command = sys.argv[3]
    args = sys.argv[4:]

    try:
        pantry = Pantry(path)
        if command == "add":
            if len(args) != 2: raise ValueError()
            pantry.add(args[0], int(args[1]))
        elif command == "take":
            if len(args) != 2: raise ValueError()
            pantry.take(args[0], int(args[1]))
        elif command == "list":
            pass
        else:
            raise ValueError()
        
        if command == "list":
            for item in pantry.list_items():
                print(f"MENGE {item['qty']} {item['name']}")
    except (ValueError, IndexError):
        sys.stderr.write("Error\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
