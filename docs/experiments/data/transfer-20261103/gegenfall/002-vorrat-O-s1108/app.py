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
                        raise ValueError
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
            raise ValueError
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError
        name = name.strip()
        self.items[name] = self.items.get(name, 0) + qty
        self._save()

    def take(self, name, qty):
        if not name or name.isspace():
            raise ValueError
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError
        name = name.strip()
        if name not in self.items:
            raise ValueError
        if self.items[name] < qty:
            raise ValueError
        self.items[name] -= qty
        if self.items[name] == 0:
            del self.items[name]
        self._save()

    def list(self):
        result = [{"name": k, "qty": v} for k, v in self.items.items()]
        return sorted(result, key=lambda x: x["name"])

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        path = args[0]
        cmd = args[1]
        params = args[2:]
        
        pantry = Pantry(path)
        
        if cmd == "add":
            if len(params) != 2: raise ValueError
            pantry.add(params[0], int(params[1]))
        elif cmd == "take":
            if len(params) != 2: raise ValueError
            pantry.take(params[0], int(params[1]))
        elif cmd == "list":
            for item in pantry.list():
                print(f"MENGE {item['qty']} {item['name']}")
        else:
            sys.exit(1)
            
    except (ValueError, IndexError, TypeError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
