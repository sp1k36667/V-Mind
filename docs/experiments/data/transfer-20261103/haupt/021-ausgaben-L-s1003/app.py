import sys
import json
import os

class ExpenseLog:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    content = json.load(f)
                    if not isinstance(content, dict) or "next_id" not in content or "items" not in content:
                        raise ValueError("Invalid format")
                    self.data = content
                    # Ensure IDs are handled as strings internally for JSON consistency
                    self.data["items"] = {int(k): v for k, v in content["items"].items()}
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, text, cents):
        if not text or not text.strip():
            raise ValueError("Text required")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Cents must be > 0")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"text": text, "cents": cents}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys())
        return [{"id": i, **self.data["items"][i]} for i in sorted_ids]

    def set_cents(self, id_val, cents):
        if id_val not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Cents must be > 0")
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
        print("Usage: python3 app.py --file PATH COMMAND [ARGS]", file=sys.stderr)
        sys.exit(1)
    
    if sys.argv[1] != "--file":
        print("Usage: python3 app.py --file PATH COMMAND [ARGS]", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[2]
    cmd = sys.argv[3]
    args = sys.argv[4:]

    try:
        log = ExpenseLog(path)
        if cmd == "add":
            if len(args) < 2: raise ValueError()
            log.add(args[0], int(args[1]))
        elif cmd == "list":
            for item in log.list():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif cmd == "set":
            log.set_cents(int(args[0]), int(args[1]))
        elif cmd == "remove":
            log.remove(int(args[0]))
        elif cmd == "total":
            print(log.total())
        else:
            print("Unknown command", file=sys.stderr)
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
