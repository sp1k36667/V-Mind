import sys
import json
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
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
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
        self.data["items"][str(new_id)] = {"text": text, "cents": cents}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        items = []
        for k, v in self.data["items"].items():
            items.append({"id": int(k), "text": v["text"], "cents": v["cents"]})
        return sorted(items, key=lambda x: x["id"])

    def set_cents(self, id_str, cents):
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        self._validate_cents(cents)
        self.data["items"][id_str]["cents"] = cents
        self._save()

    def remove(self, id_str):
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id_str]
        self._save()

    def total(self):
        return sum(item["cents"] for item in self.data["items"].values())

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        file_path = args[0]
        cmd = args[1]
        params = args[2:]

        log = ExpenseLog(file_path)

        if cmd == "add" and len(params) == 2:
            log.add(params[0], int(params[1]))
        elif cmd == "list":
            for item in log.list():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif cmd == "set" and len(params) == 2:
            log.set_cents(params[0], int(params[1]))
        elif cmd == "remove" and len(params) == 1:
            log.remove(params[0])
        elif cmd == "total":
            print(log.total())
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
