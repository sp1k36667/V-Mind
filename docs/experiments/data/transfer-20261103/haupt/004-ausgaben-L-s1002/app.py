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
                        raise ValueError
                    self.data = content
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file.")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, text, cents):
        if not text or not text.strip():
            raise ValueError("Empty text.")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Invalid cents.")
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"text": text, "cents": cents}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list_items(self):
        items = []
        for k, v in self.data["items"].items():
            items.append({"id": int(k), **v})
        return sorted(items, key=lambda x: x["id"])

    def set_cents(self, entry_id, cents):
        if str(entry_id) not in self.data["items"]:
            raise ValueError("ID not found.")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Invalid cents.")
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
    if len(sys.argv) < 4:
        return
    
    path = sys.argv[1]
    command = sys.argv[2]
    args = sys.argv[3:]

    try:
        log = ExpenseLog(path)
        if command == "add":
            if len(args) != 2: raise ValueError()
            log.add(args[0], int(args[1]))
        elif command == "list":
            for item in log.list_items():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif command == "set":
            if len(args) != 2: raise ValueError()
            log.set_cents(int(args[0]), int(args[1]))
        elif command == "remove":
            if len(args) != 1: raise ValueError()
            log.remove(int(args[0]))
        elif command == "total":
            print(log.total())
        else:
            raise ValueError()
    except ValueError as e:
        sys.stderr.write(str(e) if str(e) else "Error\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
