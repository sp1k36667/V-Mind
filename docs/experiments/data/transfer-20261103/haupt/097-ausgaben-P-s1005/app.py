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
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

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
        sorted_items = []
        for idx, val in sorted(self.data["items"].items()):
            sorted_items.append({"id": idx, **val})
        return sorted_items

    def set_cents(self, item_id, cents):
        if item_id not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Cents must be > 0")
        self.data["items"][item_id]["cents"] = cents
        self._save()

    def remove(self, item_id):
        if item_id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][item_id]
        self._save()

    def total(self):
        return sum(item["cents"] for item in self.data["items"].values())

def main():
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(1)
    
    file_path = args[0]
    command = args[1]
    
    try:
        log = ExpenseLog(file_path)
        if command == "add" and len(args) == 4:
            log.add(args[2], int(args[3]))
        elif command == "list":
            for item in log.list():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif command == "set" and len(args) == 4:
            log.set_cents(int(args[2]), int(args[3]))
        elif command == "remove" and len(args) == 3:
            log.remove(int(args[2]))
        elif command == "total":
            print(log.total())
        else:
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    main()
