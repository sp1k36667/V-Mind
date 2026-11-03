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
        if not text or not text.strip():
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

    def set_cents(self, id_str, cents):
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Invalid cents")
        self.data["items"][id_str]["cents"] = cents
        self.save()

    def remove(self, id_str):
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id_str]
        self.save()

    def total(self):
        return sum(int(v["cents"]) for v in self.data["items"].values())

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3 or args[0] != "--file":
            sys.exit(1)
        
        path = args[1]
        cmd = args[2]
        log = ExpenseLog(path)

        if cmd == "add":
            if len(args) != 5: raise ValueError()
            log.add(args[3], int(args[4]))
        elif cmd == "list":
            for item in log.list_items():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif cmd == "set":
            if len(args) != 5: raise ValueError()
            log.set_cents(args[3], int(args[4]))
        elif cmd == "remove":
            if len(args) != 4: raise ValueError()
            log.remove(args[3])
        elif cmd == "total":
            print(log.total())
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"{str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
