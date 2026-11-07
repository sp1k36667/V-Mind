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
                    content = json.load(f)
                    if not isinstance(content, dict) or "items" not in content or not isinstance(content["items"], dict):
                        raise ValueError("Invalid format")
                    self.data = content
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")

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
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Invalid quantity")
        if name not in self.data["items"]:
            raise ValueError("Unknown item")
        current = self.data["items"][name]
        if qty > current:
            raise ValueError("Not enough quantity")
        self.data["items"][name] -= qty
        if self.data["items"][name] == 0:
            del self.data["items"][name]
        self._save()

    def list(self):
        res = [{"name": k, "qty": v} for k, v in self.data["items"].items()]
        res.sort(key=lambda x: x["name"])
        return res

def main():
    if len(sys.argv) < 5:
        sys.stderr.write("Usage: python3 app.py --file PATH COMMAND [ARGS]\n")
        sys.exit(1)
    
    try:
        path = sys.argv[2]
        cmd = sys.argv[3]
        pantry = Pantry(path)
        
        if cmd == "add":
            pantry.add(sys.argv[4], int(sys.argv[5]))
        elif cmd == "take":
            pantry.take(sys.argv[4], int(sys.argv[5]))
        elif cmd == "list":
            for item in pantry.list():
                print(f"{item['qty']} {item['name']}")
        else:
            sys.stderr.write("Unknown command\n")
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
