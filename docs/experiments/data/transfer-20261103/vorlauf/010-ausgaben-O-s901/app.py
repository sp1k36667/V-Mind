import sys
import json
import os

class ExpenseLog:
    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                if "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.data = data
            except (json.JSONDecodeError, ValueError, KeyError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, text, cents):
        if not text or not text.strip():
            raise ValueError("Empty text")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Invalid cents")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"text": text, "cents": cents}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        res = []
        for i in sorted(self.data["items"].keys()):
            item = self.data["items"][i]
            res.append({"id": i, "text": item["text"], "cents": item["cents"]})
        return res

    def set_cents(self, id_val, cents):
        if id_val not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Invalid cents")
        self.data["items"][id_val]["cents"] = cents
        self._save()

    def remove(self, id_val):
        if id_val not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id_val]
        self._save()

    def total(self):
        return sum(item["cents"] for item in self.data["items"].values())

def main():
    args = sys.argv[1:]
    if len(args) < 3:
        sys.stderr.write("Usage: app.py --file PATH COMMAND [ARGS]\n")
        sys.exit(1)
    
    if args[0] != "--file":
        sys.stderr.write("Missing --file\n")
        sys.exit(1)
        
    path = args[1]
    cmd = args[2]
    params = args[3:]

    try:
        log = ExpenseLog(path)
        if cmd == "add":
            if len(params) != 2: raise ValueError()
            log.add(params[0], int(params[1]))
        elif cmd == "list":
            for item in log.list():
                print(f"{item['id']} {item['cents']} ct {item['text']}")
        elif cmd == "set":
            if len(params) != 2: raise ValueError()
            log.set_cents(int(params[0]), int(params[1]))
        elif cmd == "remove":
            if len(params) != 1: raise ValueError()
            log.remove(int(params[0]))
        elif cmd == "total":
            print(log.total())
        else:
            sys.stderr.write("Unknown command\n")
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
