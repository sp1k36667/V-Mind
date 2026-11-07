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
                    content = json.load(f)
                    if not isinstance(content, dict) or "items" not in content:
                        raise ValueError()
                    self.data = content
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, name, qty):
        name = name.strip()
        if not name:
            raise ValueError()
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError()
        
        items = self.data["items"]
        items[name] = items.get(name, 0) + qty
        self._save()

    def take(self, name, qty):
        name = name.strip()
        if not name:
            raise ValueError()
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError()
        
        items = self.data["items"]
        if name not in items or items[name] < qty:
            raise ValueError()
        
        items[name] -= qty
        if items[name] == 0:
            del items[name]
        self._save()

    def list(self):
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
                raise ValueError()
            pantry.add(args.args[0], int(args.args[1]))
        elif args.command == "take":
            if len(args.args) < 2:
                raise ValueError()
            pantry.take(args.args[0], int(args.args[1]))
        elif args.command == "list":
            for item in pantry.list():
                print(f"{item['qty']} {item['name']}")
    except (ValueError, IndexError, TypeError) as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
