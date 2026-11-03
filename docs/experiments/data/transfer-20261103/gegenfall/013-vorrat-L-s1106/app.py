import json
import sys
import argparse
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
            except (json.JSONDecodeError, ValueError):
                raise ValueError("File is corrupted")

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
        
        if name not in self.data["items"]:
            raise ValueError("Unknown item")
        
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
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()

    try:
        pantry = Pantry(args.file)
        if args.command == "add":
            if len(args.args) < 2:
                raise ValueError("Missing arguments")
            pantry.add(args.args[0], int(args.args[1]))
        elif args.command == "take":
            if len(args.args) < 2:
                raise ValueError("Missing arguments")
            pantry.take(args.args[0], int(args.args[1]))
        elif args.command == "list":
            for item in pantry.list_items():
                print(f"QTY {item['qty']} {item['name']}")
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
