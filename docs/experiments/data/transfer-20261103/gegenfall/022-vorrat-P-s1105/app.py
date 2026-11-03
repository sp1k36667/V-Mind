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
                raise ValueError("File corrupted")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, name, qty):
        name = name.strip()
        if not name:
            raise ValueError
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError
        self.data["items"][name] = self.data["items"].get(name, 0) + qty
        self._save()

    def take(self, name, qty):
        name = name.strip()
        if not name:
            raise ValueError
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError
        if name not in self.data["items"]:
            raise ValueError
        if self.data["items"][name] < qty:
            raise ValueError
        self.data["items"][name] -= qty
        if self.data["items"][name] == 0:
            del self.data["items"][name]
        self._save()

    def list_items(self):
        res = [{"name": k, "qty": v} for k, v in self.data["items"].items()]
        return sorted(res, key=lambda x: x["name"])

def main():
    try:
        if len(sys.argv) < 3:
            sys.exit(1)
        path = sys.argv[1]
        cmd = sys.argv[2]
        pantry = Pantry(path)

        if cmd == "add":
            if len(sys.argv) < 5: raise ValueError
            pantry.add(sys.argv[3], int(sys.argv[4]))
        elif cmd == "take":
            if len(sys.argv) < 5: raise ValueError
            pantry.take(sys.argv[3], int(sys.argv[4]))
        elif cmd == "list":
            for item in pantry.list_items():
                print(f"{item['qty']} {item['name']}")
        else:
            sys.exit(1)
    except (ValueError, IndexError, TypeError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
