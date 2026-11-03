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
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.data = data
            except (json.JSONDecodeError, ValueError, KeyError):
                raise ValueError("Damaged JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_cents(self, cents):
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Cents must be a positive integer")

    def add(self, text, cents):
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        self._validate_cents(cents)
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"text": text, "cents": cents}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        result = []
        for i in sorted(self.data["items"].keys()):
            item = self.data["items"][i]
            result.append({"id": i, "text": item["text"], "cents": item["cents"]})
        return result

    def set_cents(self, id_val, cents):
        if id_val not in self.data["items"]:
            raise ValueError("ID not found")
        self._validate_cents(cents)
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
    if len(sys.argv) < 4:
        sys.stderr.write("Usage: python3 app.py --file PATH COMMAND [ARGS]\n")
        sys.exit(1)
    
    if sys.argv[1] != "--file":
        sys.stderr.write("Invalid arguments\n")
        sys.exit(1)
        
    path = sys.argv[2]
    cmd = sys.argv[3]
    args = sys.argv[4:]

    try:
        log = ExpenseLog(path)
        if cmd == "add":
            if len(args) != 2: raise ValueError()
            id_res = log.add(args[0], int(args[1]))
            print(id_res)
        elif cmd == "list":
            for item in log.list():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif cmd == "set":
            if len(args) != 2: raise ValueError()
            log.set_cents(int(args[0]), int(args[1]))
        elif cmd == "remove":
            if len(args) != 1: raise ValueError()
            log.remove(int(args[0]))
        elif cmd == "total":
            print(log.total())
        else:
            sys.stderr.write("Unknown command\n")
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
