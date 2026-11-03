import sys
import json
import os

class ExpenseLog:
    def __init__(self, path):
        self.path = path
        self.data = self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return {"next_id": 1, "items": {}}
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                raise ValueError("Invalid format")
            return data
        except (json.JSONDecodeError, ValueError, KeyError):
            raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def _validate_cents(self, cents):
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Cents must be a positive integer")

    def add(self, text, cents):
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
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

    def set_cents(self, id_val, cents):
        if str(id_val) not in self.data["items"]:
            raise ValueError("ID not found")
        self._validate_cents(cents)
        self.data["items"][str(id_val)]["cents"] = cents
        self._save()

    def remove(self, id_val):
        if str(id_val) not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(id_val)]
        self._save()

    def total(self):
        return sum(int(v["cents"]) for v in self.data["items"].values())

def main():
    if len(sys.argv) < 3:
        sys.exit(1)
    
    path = sys.argv[1]
    try:
        log = ExpenseLog(path)
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    cmd = sys.argv[2]
    try:
        if cmd == "add" and len(sys.argv) == 5:
            log.add(sys.argv[3], int(sys.argv[4]))
        elif cmd == "list":
            for item in log.list_items():
                sys.stdout.write(f"{item['id']} {item['cents']} {item['text']}\n")
        elif cmd == "set" and len(sys.argv) == 5:
            log.set_cents(int(sys.argv[3]), int(sys.argv[4]))
        elif cmd == "remove" and len(sys.argv) == 4:
            log.remove(int(sys.argv[3]))
        elif cmd == "total":
            sys.stdout.write(f"{log.total()}\n")
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
