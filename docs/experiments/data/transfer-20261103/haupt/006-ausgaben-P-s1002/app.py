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
                    content = f.read()
                    if not content.strip():
                        raise ValueError("Empty file")
                    self.data = json.load(f)
                    if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                        raise ValueError("Invalid format")
            except (json.JSONDecodeError, ValueError):
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
        self.data["items"][str(new_id)] = {"text": text, "cents": cents}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list_items(self):
        sorted_ids = sorted(self.data["items"].keys(), key=int)
        result = []
        for sid in sorted_ids:
            item = self.data["items"][sid]
            result.append({"id": int(sid), "text": item["text"], "cents": item["cents"]})
        return result

    def set_cents(self, id_val, cents):
        if not isinstance(id_val, int) or str(id_val) not in self.data["items"]:
            raise ValueError("Invalid ID")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Cents must be > 0")
        self.data["items"][str(id_val)] = {"text": self.data["items"][str(id_val)]["text"], "cents": cents}
        self._save()

    def remove(self, id_val):
        if not isinstance(id_val, int) or str(id_val) not in self.data["items"]:
            raise ValueError("Invalid ID")
        del self.data["items"][str(id_val)]
        self._save()

    def total(self):
        return sum(int(item["cents"]) for item in self.data["items"].values())

def main():
    if len(sys.argv) < 4:
        sys.exit(1)
    
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
                print(f"{item['id']} {item['cents']} ct {item['text']}")
        elif command == "set":
            if len(args) != 2: raise ValueError()
            log.set_cents(int(args[0]), int(args[1]))
        elif command == "remove":
            if len(args) != 1: raise ValueError()
            log.remove(int(args[0]))
        elif command == "total":
            print(log.total())
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
