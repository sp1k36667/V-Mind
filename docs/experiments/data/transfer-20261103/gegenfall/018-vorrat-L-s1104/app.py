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
                self.data = json.load(f)
                if not isinstance(self.data, dict) or "items" not in self.data:
                    raise ValueError("Invalid format")
                if not isinstance(self.data["items"], dict):
                    raise ValueError("Items must be a dict")
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, ValueError):
            raise ValueError("Corrupted or invalid JSON file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, name, qty):
        if not name or name.isspace():
            raise ValueError("Name cannot be empty")
        name = name.strip()
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Quantity must be a positive integer")
        
        current = self.data["items"].get(name, 0)
        self.data["items"][name] = current + qty
        self._save()

    def take(self, name, qty):
        if not name or name.isspace():
            raise ValueError("Name cannot be empty")
        name = name.strip()
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Quantity must be a positive integer")
        
        if name not in self.data["items"]:
            raise ValueError("Item not found")
        
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
        items = []
        for name, qty in self.data["items"].items():
            items.append({"name": name, "qty": qty})
        return sorted(items, key=lambda x: x["name"])

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
                raise ValueError("Missing arguments for add")
            pantry.add(args.args[0], int(args.args[1]))
        elif args.command == "take":
            if len(args.args) < 2:
                raise ValueError("Missing arguments for take")
            pantry.take(args.args[0], int(args.args[1]))
        elif args.command == "list":
            for item in pantry.list_items():
                print(f"MENGE {item['qty']} {item['name']}")
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
