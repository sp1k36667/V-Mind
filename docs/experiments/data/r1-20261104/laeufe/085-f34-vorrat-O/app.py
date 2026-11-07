import sys
import json
import os

class Pantry:
    def __init__(self, path):
        self.path = path
        self.data = {"items": {}}
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    content = f.read()
                    loaded = json.loads(content)
                    if not isinstance(loaded, dict) or "items" not in loaded or not isinstance(loaded["items"], dict):
                        raise ValueError
                    self.data = loaded
            except (json.JSONDecodeError, ValueError, IOError):
                raise ValueError("File is corrupted or invalid.")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, name, qty):
        if not name or name.isspace():
            raise ValueError
        name = name.strip()
        if not name:
            raise ValueError
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError
        
        current = self.data["items"].get(name, 0)
        self.data["items"][name] = current + qty
        self._save()

    def take(self, name, qty):
        if not name or name.isspace():
            raise ValueError
        name = name.strip()
        if not name:
            raise ValueError
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError
        
        if name not in self.data["items"]:
            raise ValueError
        
        current = self.data["items"][name]
        if qty > current:
            raise ValueError
        
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
    if len(sys.argv) < 4 or sys.argv[1] != "--file":
        print("Usage: python3 app.py --file PATH COMMAND [ARGS]", file=sys.stderr)
        sys.exit(1)
    
    path = sys.argv[2]
    cmd = sys.argv[3]
    args = sys.argv[4:]

    try:
        pantry = Pantry(path)
        if cmd == "add" and len(args) == 2:
            pantry.add(args[0], int(args[1]))
        elif cmd == "take" and len(args) == 2:
            pantry.take(args[0], int(args[1]))
        elif cmd == "list":
            for item in pantry.list():
                print(f"{item['qty']} {item['name']}")
        else:
            print("Invalid command or arguments", file=sys.stderr)
            sys.exit(1)
    except ValueError as e:
        print(str(e) if str(e) else "Error", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
