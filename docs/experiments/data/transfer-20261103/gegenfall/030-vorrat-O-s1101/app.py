import json
import sys
import argparse
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
            raise ValueError("Empty name")
        name = name.strip()
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Invalid quantity")
        self.data["items"][name] = self.data["items"].get(name, 0) + qty
        self._save()

    def take(self, name, qty):
        if not name or name.isspace():
            raise ValueError("Empty name")
        name = name.strip()
        if name not in self.data["items"]:
            raise ValueError("Unknown item")
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Invalid quantity")
        
        new_qty = self.data["items"][name] - qty
        if new_qty < 0:
            raise ValueError("Insufficient quantity")
        
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
            if len(args.args) != 2:
                raise ValueError("Usage: add NAME QTY")
            pantry.add(args.args[0], int(args.args[1]))
        elif args.command == "take":
            if len(args.args) != 2:
                raise ValueError("Usage: take NAME QTY")
            pantry.take(args.args[0], int(args.args[1]))
        elif args.command == "list":
            for item in pantry.list_items():
                print(f"QTY {item['qty']} NAME {item['name']}")
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
