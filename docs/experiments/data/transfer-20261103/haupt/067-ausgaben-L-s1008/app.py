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
                    loaded = json.load(f)
                    if not isinstance(loaded, dict) or "next_id" not in loaded or "items" not in loaded:
                        raise ValueError
                    self.data = loaded
                    # Ensure keys are treated as ints internally if possible, 
                    # but JSON keys are always strings. We'll handle conversion.
            except (json.JSONDecodeError, ValueError):
                raise ValueError("File corrupted")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, text, cents):
        if not text or text.isspace():
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
        for i_str in sorted_ids:
            item = self.data["items"][i_str]
            result.append({"id": int(i_str), **item})
        return result

    def set_cents(self, i_str, cents):
        if i_str not in self.data["items"]:
            raise ValueError("ID not found")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Cents must be > 0")
        self.data["items"][i_str]["cents"] = cents
        self._save()

    def remove(self, i_str):
        if i_str not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][i_str]
        self._save()

    def total(self):
        return sum(item["cents"] for item in self.data["items"].values())

def main():
    if len(sys.argv) < 3:
        sys.exit(1)
    
    file_path = sys.argv[1]
    command = sys.argv[2]
    args = sys.argv[3:]

    try:
        log = ExpenseLog(file_path)
        if command == "add":
            if len(args) < 2: raise ValueError
            text = args[0]
            cents = int(args[1])
            log.add(text, cents)
        elif command == "list":
            for item in log.list_items():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif command == "set":
            if len(args) < 2: raise ValueError
            log.set_cents(args[0], int(args[1]))
        elif command == "remove":
            if len(args) < 1: raise ValueError
            log.remove(args[0])
        elif command == "total":
            print(log.total())
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
