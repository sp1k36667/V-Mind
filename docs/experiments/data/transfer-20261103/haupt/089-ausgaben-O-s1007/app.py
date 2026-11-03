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
                raise ValueError(f"Corrupted file: {self.path}")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_cents(self, cents):
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Cents must be a positive integer.")

    def add(self, text, cents):
        if not text or not text.strip():
            raise ValueError("Text cannot be empty.")
        self._validate_cents(cents)
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"text": text, "cents": cents}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list_items(self):
        items = []
        for k, v in self.data["items"].items():
            items.append({"id": int(k), "text": v["text"], "cents": v["cents"]})
        return sorted(items, key=lambda x: x["id"])

    def set_cents(self, entry_id, cents):
        if str(entry_id) not in self.data["items"]:
            raise ValueError("ID not found.")
        self._validate_cents(cents)
        self.data["items"][str(entry_id)]["cents"] = cents
        self._save()

    def remove(self, entry_id):
        if str(entry_id) not in self.data["items"]:
            raise ValueError("ID not found.")
        del self.data["items"][str(entry_id)]
        self._save()

    def total(self):
        return sum(int(v["cents"]) for v in self.data["items"].values())

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 2:
            sys.exit(1)
        path = args[0]
        cmd = args[1]
        log = ExpenseLog(path)

        if cmd == "add":
            if len(args) < 4: raise ValueError()
            log.add(args[2], int(args[3]))
        elif cmd == "list":
            for item in log.list_items():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif cmd == "set":
            if len(args) < 4: raise ValueError()
            log.set_cents(int(args[2]), int(args[3]))
        elif cmd == "remove":
            if len(args) < 3: raise ValueError()
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
