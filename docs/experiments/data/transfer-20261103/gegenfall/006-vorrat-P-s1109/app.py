import json
import sys
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
                        raise ValueError()
                    self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, name, qty):
        if not name or name.isspace():
            raise ValueError()
        name = name.strip()
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError()
        
        current = self.data["items"].get(name, 0)
        self.data["items"][name] = current + qty
        self._save()

    def take(self, name, qty):
        if not name or name.isspace():
            raise ValueError()
        name = name.strip()
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError()
        
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
        items = []
        for name, qty in self.data["items"].items():
            items.append({"name": name, "qty": qty})
        return sorted(items, key=lambda x: x["name"])

def main():
    try:
        if len(sys.argv) < 4:
            sys.exit(1)
        
        path = sys.argv[1]
        command = sys.argv[2]
        args = sys.argv[3:]
        
        pantry = Pantry(path)
        
        if command == "add":
            if len(args) != 2:
                sys.exit(1)
            pantry.add(args[0], int(args[1]))
        elif command == "take":
            if len(args) != 2:
                sys.exit(1)
            pantry.take(args[0], int(args[1]))
        elif command == "list":
            for item in pantry.list_items():
                print(f"QTY {item['qty']} NAME {item['name']}")
        else:
            sys.exit(1)
            
    except (ValueError, IndexError, TypeError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
