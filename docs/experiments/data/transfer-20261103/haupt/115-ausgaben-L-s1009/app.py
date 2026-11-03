import sys
import json
import os

class ExpenseLog:
    def __init__(self, path):
        self.path = path
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                if "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.next_id = data["next_id"]
                self.items = data["items"]
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")
        else:
            self.next_id = 1
            self.items = {}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump({"next_id": self.next_id, "items": self.items}, f)

    def add(self, text, cents):
        if not text or text.isspace():
            raise ValueError("Empty text")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Invalid cents")
        id_ = self.next_id
        self.items[str(id_)] = {"text": text, "cents": cents}
        self.next_id += 1
        self._save()
        return id_

    def list(self):
        res = []
        for k, v in self.items.items():
            res.append({"id": int(k), "text": v["text"], "cents": v["cents"]})
        return sorted(res, key=lambda x: x["id"])

    def set_cents(self, id_val, cents):
        if str(id_val) not in self.items:
            raise ValueError("ID not found")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Invalid cents")
        self.items[str(id_val)]["cents"] = cents
        self._save()

    def remove(self, id_val):
        if str(id_val) not in self.items:
            raise ValueError("ID not found")
        del self.items[str(id_val)]
        self._save()

    def total(self):
        return sum(v["cents"] for v in self.items.values())

def main():
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(1)
    path = args[0]
    cmd = args[1]
    try:
        log = ExpenseLog(path)
        if cmd == "add" and len(args) == 3:
            _, c = args[2].split()
            print(log.add(args[2], int(c)))
        elif cmd == "list":
            for item in log.list():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif cmd == "set" and len(args) == 4:
            log.set_cents(int(args[2]), int(args[3]))
        elif cmd == "remove" and len(args) == 3:
            log.remove(int(args[2]))
        elif cmd == "total":
            print(log.total())
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
