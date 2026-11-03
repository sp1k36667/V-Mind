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
                    self.data = json.load(f)
                    if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                        raise ValueError
            except (json.JSONDecodeError, ValueError):
                raise ValueError("File corrupted")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, text, cents):
        if not text or not text.strip():
            raise ValueError("Text required")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Cents must be > 0")
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"text": text, "cents": cents}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        res = []
        for k, v in self.data["items"].items():
            res.append({"id": int(k), "text": v["text"], "cents": v["cents"]})
        return sorted(res, key=lambda x: x["id"])

    def set_cents(self, id_val, cents):
        if not str(id_val).isdigit() or id_val not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Cents must be > 0")
        self.data["items"][str(id_val)] = {"text": self.data["items"][str(id_val)]["text"], "cents": cents}
        self._save()

    def remove(self, id_val):
        if not str(id_val).isdigit() or id_val not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(id_val)]
        self._save()

    def total(self):
        return sum(v["cents"] for v in self.data["items"].values())

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            print("Usage: python3 app.py --file PATH COMMAND [ARGS]", file=sys.stderr)
            sys.exit(1)
        
        path = args[1].replace("--file ", "")
        if path.startswith("--file "):
            path = args[1][7:]
        
        log = ExpenseLog(path)
        cmd = args[2]
        
        if cmd == "add":
            log.add(args[3], int(args[4]))
        elif cmd == "list":
            for item in log.list():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif cmd == "set":
            log.set_cents(int(args[3]), int(args[4]))
        elif cmd == "remove":
            log.remove(int(args[3]))
        elif cmd == "total":
            print(log.total())
        else:
            print("Unknown command", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
