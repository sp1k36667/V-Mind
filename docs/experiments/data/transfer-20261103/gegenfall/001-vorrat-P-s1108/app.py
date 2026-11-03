import sys
import json
import os

class Pantry:
    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                    if not isinstance(data, dict) or "items" not in data:
                        raise ValueError("Invalid format")
                    self.items = data["items"]
            except (json.JSONDecodeError, ValueError, KeyError):
                raise ValueError("Corrupted file")
        else:
            self.items = {}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump({"items": self.items}, f)

    def add(self, name, qty):
        if not name or name.isspace():
            raise ValueError("Empty name")
        name = name.strip()
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Invalid quantity")
        self.items[name] = self.items.get(name, 0) + qty
        self._save()

    def take(self, name, qty):
        if not name or name.isspace():
            raise ValueError("Empty name")
        name = name.strip()
        if name not in self.items:
            raise ValueError("Unknown item")
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Invalid quantity")
        if self.items[name] < qty:
            raise ValueError("Insufficient quantity")
        self.items[name] -= qty
        if self.items[name] == 0:
            del self.items[name]
        self._save()

    def list(self):
        res = [{"name": k, "qty": v} for k, v in self.items.items()]
        return sorted(res, key=lambda x: x["name"])

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        path = args[0]
        cmd = args[1]
        params = args[2:]
        
        p = Pantry(path)
        
        if cmd == "add":
            if len(params) != 2: raise ValueError()
            p.add(params[0], int(params[1]))
        elif cmd == "take":
            if len(params) != 2: raise ValueError()
            p.take(params[0], int(params[1]))
        elif cmd == "list":
            pass
        else:
            raise ValueError()
            
        if cmd == "list":
            for item in p.list():
                print(f"MENGE {item['qty']} {item['name']}")
                
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
