import json
import sys
import argparse
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
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self.save()

    def save(self):
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
        self.save()
        return new_id

    def list_items(self):
        res = []
        for idx, val in sorted(self.data["items"].items()):
            res.append({"id": idx, "text": val["text"], "cents": val["cents"]})
        return res

    def set_cents(self, idx, cents):
        if idx not in self.data["items"]:
            raise ValueError("ID not found")
        self._validate_cents(cents)
        self.data["items"][idx]["cents"] = cents
        self.save()

    def remove(self, idx):
        if idx not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][idx]
        self.save()

    def total(self):
        return sum(item["cents"] for item in self.data["items"].values())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("command", nargs=1)
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()

    try:
        log = ExpenseLog(args.file)
        cmd = args.command[0]
        
        if cmd == "add":
            log.add(args.args[0], int(args.args[1]))
        elif cmd == "list":
            for item in log.list_items():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif cmd == "set":
            log.set_cents(int(args.args[0]), int(args.args[1]))
        elif cmd == "remove":
            log.remove(int(args.args[0]))
        elif cmd == "total":
            print(log.total())
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
