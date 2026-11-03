import json
import sys
import argparse
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
            except (json.JSONDecodeError, ValueError, KeyError, TypeError):
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
        self.data["items"][str(new_id)] = {"text": text, "cents": cents}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        items = []
        for k, v in self.data["items"].items():
            items.append({"id": int(k), "text": v["text"], "cents": v["cents"]})
        return sorted(items, key=lambda x: x["id"])

    def set_cents(self, entry_id, cents):
        if str(entry_id) not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Invalid cents")
        self.data["items"][str(entry_id)]["cents"] = cents
        self._save()

    def remove(self, entry_id):
        if str(entry_id) not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(entry_id)]
        self._save()

    def total(self):
        return sum(int(v["cents"]) for v in self.data["items"].values())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("command", choices=["add", "list", "set", "remove", "total"])
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()

    try:
        log = ExpenseLog(args.file)
        if args.command == "add":
            if len(args.args) < 2: raise ValueError("Missing args")
            log.add(args.args[0], int(args.args[1]))
        elif args.command == "list":
            for item in log.list():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif args.command == "set":
            if len(args.args) < 2: raise ValueError("Missing args")
            log.set_cents(int(args.args[0]), int(args.args[1]))
        elif args.command == "remove":
            if len(args.args) < 1: raise ValueError("Missing args")
            log.remove(int(args.args[0]))
        elif args.command == "total":
            print(log.total())
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
