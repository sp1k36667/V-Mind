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
                    raise ValueError
                self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("File corrupted")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_cents(self, cents):
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError
        return cents

    def add(self, text, cents):
        if not text or not text.strip():
            raise ValueError
        cents = self._validate_cents(cents)
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
            raise ValueError
        cents = self._validate_cents(cents)
        self.data["items"][id_val]["cents"] = cents
        self._save()

    def remove(self, id_val):
        if id_val not in self.data["items"]:
            raise ValueError
        del self.data["items"][id_val]
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
            if len(args) < 4: raise ValueError
            log.add(args[2], int(args[3]))
        elif cmd == "list":
            for item in log.list():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif cmd == "set":
            if len(args) < 5: raise ValueError
            log.set_cents(int(args[2]), int(args[3]))
        elif cmd == "remove":
            if len(args) < 4: raise ValueError
            log.remove(int(args[2]))
        elif cmd == "total":
            print(log.total())
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
