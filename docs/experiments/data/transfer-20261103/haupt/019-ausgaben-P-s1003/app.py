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
                self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self.save()

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, text, cents):
        if not text or text.isspace():
            raise ValueError("Empty text")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Invalid cents")
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"text": text, "cents": cents}
        self.data["next_id"] += 1
        self.save()
        return new_id

    def list_items(self):
        res = []
        for key, val in self.data["items"].items():
            res.append({"id": int(key), **val})
        return sorted(res, key=lambda x: x["id"])

    def set_cents(self, id_val, cents):
        if not str(id_val).isdigit() or id_val not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Invalid cents")
        self.data["items"][str(id_val)]["cents"] = cents
        self.save()

    def remove(self, id_val):
        if not str(id_val).isdigit() or id_val not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(id_val)]
        self.save()

    def total(self):
        return sum(int(v["cents"]) for v in self.data["items"].values())

def main():
    if len(sys.argv) < 4:
        sys.exit(1)
    
    path = sys.argv[1]
    cmd = sys.argv[2]
    args = sys.argv[3:]

    try:
        log = ExpenseLog(path)
        if cmd == "add":
            if len(args) != 2: raise ValueError()
            log.add(args[0], int(args[1]))
        elif cmd == "list":
            for item in log.list_items():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif cmd == "set":
            log.set_cents(int(args[0]), int(args[1]))
        elif cmd == "remove":
            log.remove(int(args[0]))
        elif cmd == "total":
            print(log.total())
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
