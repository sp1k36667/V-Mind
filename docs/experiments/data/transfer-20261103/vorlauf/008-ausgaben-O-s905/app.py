import json
import sys
import argparse

class ExpenseLog:
    def __init__(self, path):
        self.path = path
        try:
            with open(self.path, 'r') as f:
                data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.data = data
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            self.data = {"next_id": 1, "items": {}}
            self.save()

    def save(self):
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
        self.data["items"][str(new_id)] = {"text": text, "cents": cents}
        self.data["next_id"] += 1
        self.save()
        return new_id

    def list_items(self):
        items = []
        for k, v in self.data["items"].items():
            items.append({"id": int(k), "text": v["text"], "cents": v["cents"]})
        return sorted(items, key=lambda x: x["id"])

    def set_cents(self, entry_id, cents):
        if str(entry_id) not in self.data["items"]:
            raise ValueError("ID not found")
        self._validate_cents(cents)
        self.data["items"][str(entry_id)]["cents"] = cents
        self.save()

    def remove(self, entry_id):
        if str(entry_id) not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(entry_id)]
        self.save()

    def total(self):
        return sum(item["cents"] for item in self.data["items"].values())

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
            for item in log.list_items():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif args.command == "set":
            log.set_cents(int(args.args[0]), int(args.args[1]))
        elif args.command == "remove":
            log.remove(int(args.args[0]))
        elif args.command == "total":
            print(log.total())
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
