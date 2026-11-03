import json
import sys
import argparse

class Pantry:
    def __init__(self, path):
        self.path = path
        self.data = {"items": {}}
        self._load()

    def _load(self):
        try:
            with open(self.path, 'r') as f:
                data = json.load(f)
                if not isinstance(data, dict) or "items" not in data or not isinstance(data["items"], dict):
                    raise ValueError("Invalid format")
                self.data = data
        except FileNotFoundError:
            self.data = {"items": {}}
        except (json.JSONDecodeError, ValueError):
            raise ValueError("Damaged or invalid JSON file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, name, qty):
        if not name or name.isspace():
            raise ValueError("Invalid name")
        name = name.strip()
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Quantity must be a positive integer")
        self.data["items"][name] = self.data["items"].get(name, 0) + qty
        self._save()

    def take(self, name, qty):
        if not name or name.isspace():
            raise ValueError("Invalid name")
        name = name.strip()
        if name not in self.data["items"]:
            raise ValueError("Item not found")
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Quantity must be a positive integer")
        
        current = self.data["items"][name]
        if current < qty:
            raise ValueError("Not enough quantity")
        
        new_qty = current - qty
        if new_qty == 0:
            del self.data["items"][name]
        else:
            self.data["items"][name] = new_qty
        self._save()

    def list_items(self):
        res = []
        for name, qty in self.data["items"].items():
            res.append({"name": name, "qty": qty})
        return sorted(res, key=lambda x: x["name"])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("command", choices=["add", "take", "list"])
    parser.add_argument("args", nargs=argparse.REMAINDER)
    
    try:
        args = parser.parse_args()
        pantry = Pantry(args.file)
        
        if args.command == "add":
            if len(args.args) < 2:
                raise ValueError("Missing arguments for add")
            pantry.add(args.args[0], int(args.args[1]))
        elif args.command == "take":
            if len(args.args) < 2:
                raise ValueError("Missing arguments for take")
            pantry.take(args.args[0], int(args.args[1]))
        elif args.command == "list":
            items = pantry.list_items()
            for item in items:
                print(f"MENGE {item['qty']} {item['name']}")
                
    except (ValueError, IndexError, TypeError) as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
