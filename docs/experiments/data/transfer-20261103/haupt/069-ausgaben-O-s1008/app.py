import json
import sys
import argparse

class ExpenseLog:
    def __init__(self, path):
        self.path = path
        self.data = self._load()

    def _load(self):
        try:
            with open(self.path, 'r') as f:
                data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError
                return data
        except FileNotFoundError:
            return {"next_id": 1, "items": {}}
        except (json.JSONDecodeError, ValueError):
            raise ValueError(f"File {self.path} is corrupted.")

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
        self.data["items"][new_id] = {"text": text, "cents": cents}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list_items(self):
        sorted_ids = sorted(self.data["items"].keys())
        result = []
        for i in sorted_ids:
            item = self.data["items"][i]
            result.append({"id": i, "text": item["text"], "cents": item["cents"]})
        return result

    def set_cents(self, entry_id, cents):
        if entry_id not in self.data["items"]:
            raise ValueError(f"ID {entry_id} not found.")
        self._validate_cents(cents)
        self.data["items"][entry_id]["cents"] = cents
        self._save()

    def remove(self, entry_id):
        if entry_id not in self.data["items"]:
            raise ValueError(f"ID {entry_id} not found.")
        del self.data["items"][entry_id]
        self._save()

    def total(self):
        return sum(item["cents"] for item in self.data["items"].values())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("command", choices=["add", "list", "set", "remove", "total"])
    parser.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    try:
        log = ExpenseLog(args.file)
        if args.command == "add":
            if len(args.args) < 2: raise ValueError("Missing args.")
            log.add(args.args[0], int(args.args[1]))
        elif args.command == "list":
            for item in log.list_items():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif args.command == "set":
            if len(args.args) < 2: raise ValueError("Missing args.")
            log.set_cents(int(args.args[0]), int(args.args[1]))
        elif args.command == "remove":
            if len(args.args) < 1: raise ValueError("Missing ID.")
            log.remove(int(args.args[0]))
        elif args.command == "total":
            print(log.total())
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
