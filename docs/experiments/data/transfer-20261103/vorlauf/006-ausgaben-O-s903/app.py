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
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Damaged file")
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

    def set_cents(self, entry_id, cents):
        if entry_id not in self.data["items"]:
            raise ValueError
        cents = self._validate_cents(cents)
        self.data["items"][entry_id]["cents"] = cents
        self._save()

    def remove(self, entry_id):
        if entry_id not in self.data["items"]:
            raise ValueError
        del self.data["items"][entry_id]
        self._save()

    def total(self):
        return sum(item["cents"] for item in self.data["items"].values())

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            print("Usage: python3 app.py --file PATH COMMAND [ARGS]", file=sys.stderr)
            sys.exit(1)
        
        path = args[1]
        if args[0] != "--file":
            print("Usage: python3 app.py --file PATH COMMAND [ARGS]", file=sys.stderr)
            sys.exit(1)
            
        log = ExpenseLog(path)
        cmd = args[2]
        
        if cmd == "add":
            if len(args) < 5: raise ValueError
            log.add(args[3], int(args[4]))
        elif cmd == "list":
            for item in log.list():
                print(f"{item['id']} {item['cents']} ct {item['text']}")
        elif cmd == "set":
            if len(args) < 5: raise ValueError
            log.set_cents(int(args[3]), int(args[4]))
        elif cmd == "remove":
            if len(args) < 4: raise ValueError
            log.remove(int(args[3]))
        elif cmd == "total":
            print(log.total())
        else:
            print("Unknown command", file=sys.stderr)
            sys.exit(1)
            
    except (ValueError, IndexError, KeyError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
