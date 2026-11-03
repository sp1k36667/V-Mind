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
                    if not content:
                        raise ValueError("Empty file")
                    self.data = json.loads(content)
                    if not isinstance(self.data, dict) or "items" not in self.data:
                        raise ValueError("Invalid format")
                    if not isinstance(self.data["items"], dict):
                        raise ValueError("Invalid format")
            except (json.JSONDecodeError, ValueError):
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
        
        if name not in self.data["items"]:
            raise ValueError("Unknown item")
        
        current = self.data["items"][name]
        if qty > current:
            raise ValueError("Insufficient quantity")
        
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
        if len(sys.argv) < 4:
            sys.exit(1)
        
        path = sys.argv[1]
        cmd = sys.argv[2]
        args = sys.argv[3:]
        
        pantry = Pantry(path)
        
        if cmd == "add":
            if len(args) < 2: raise ValueError("Missing args")
            pantry.add(args[0], int(args[1]))
        elif cmd == "take":
            if len(args) < 2: raise ValueError("Missing args")
            pantry.take(args[0], int(args[1]))
        elif cmd == "list":
            for item in pantry.list_items():
                print(f"MENGE {item['qty']} {item['name']}")
        else:
            raise ValueError("Unknown command")
            
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
