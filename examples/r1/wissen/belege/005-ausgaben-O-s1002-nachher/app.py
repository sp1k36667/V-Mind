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
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.data = data
                self.data["items"] = {int(k): v for k, v in data["items"].items()}
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_cents(self, cents):
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Invalid cents")

    def add(self, text, cents):
        if not text or not text.strip():
            raise ValueError("Empty text")
        self._validate_cents(cents)
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

    def set_cents(self, entry_id, cents):
        if entry_id not in self.data["items"]:
            raise ValueError("ID not found")
        self._validate_cents(cents)
        self.data["items"][entry_id]["cents"] = cents
        self._save()

    def remove(self, entry_id):
        if entry_id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][entry_id]
        self._save()

    def total(self):
        return sum(item["cents"] for item in self.data["items"].values())

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        path = args[0]
        cmd = args[1]
        log = ExpenseLog(path)
        
        if cmd == "add":
            if len(args) < 4: raise ValueError()
            log.add(args[2], int(args[3]))
        elif cmd == "list":
            for item in log.list():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif cmd == "set":
            log.set_cents(int(args[2]), int(args[3]))
        elif cmd == "remove":
            log.remove(int(args[2]))
        elif cmd == "total":
            print(log.total())
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"{str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
