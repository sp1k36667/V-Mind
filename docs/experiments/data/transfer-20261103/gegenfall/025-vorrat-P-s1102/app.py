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
                    self.data = json.load(f)
                    if not isinstance(self.data, dict) or "items" not in self.data:
                        raise ValueError
            except (json.JSONDecodeError, ValueError):
                raise ValueError("File is corrupted")

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
        
        if name not in self.data["items"]:
            raise ValueError("Not found")
        
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
        sorted_items = sorted(self.data["items"].items())
        return [{"name": k, "qty": v} for k, v in sorted_items]

def main():
    if len(sys.argv) < 4 or sys.argv[1] != "--file":
        sys.exit(1)
    
    path = sys.argv[2]
    command = sys.argv[3]
    args = sys.argv[4:]

    try:
        pantry = Pantry(path)
        if command == "add" and len(args) == 2:
            pantry.add(args[0], int(args[1]))
        elif command == "take" and len(args) == 2:
            pantry.take(args[0], int(args[1]))
        elif command == "list":
            for item in pantry.list_items():
                print(f"QTY {item['qty']} NAME {item['name']}")
        else:
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
