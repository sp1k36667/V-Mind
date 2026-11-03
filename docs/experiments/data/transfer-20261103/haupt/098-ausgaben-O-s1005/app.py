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
            raise ValueError("Empty text")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Invalid cents")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"text": text, "cents": cents}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        result = []
        for idx in sorted(self.data["items"].keys()):
            item = self.data["items"][idx]
            result.append({"id": idx, "text": item["text"], "cents": item["cents"]})
        return result

    def set_cents(self, entry_id, cents):
        if entry_id not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Invalid cents")
        self.data["items"][entry_id]["cents"] = cents
        self._save()

    def remove(self, entry_id):
        if entry_id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][entry_id]
        self._save()

    def total(self):
        return sum(item["cents"] for item in self.data["items"].values())

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        
        file_path = args[0]
        command = args[1]
        log = ExpenseLog(file_path)

        if command == "add":
            if len(args) < 4: raise ValueError("Missing args")
            log.add(args[2], int(args[3]))
        elif command == "list":
            for item in log.list():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif command == "set":
            if len(args) < 4: raise ValueError("Missing args")
            log.set_cents(int(args[2]), int(args[3]))
        elif command == "remove":
            if len(args) < 3: raise ValueError("Missing args")
            log.remove(int(args[2]))
        elif command == "total":
            print(log.total())
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
