import sys
import json
import os

class LoanList:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    self.data = json.load(f)
                    if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                        raise ValueError
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item.strip() or not person.strip():
            raise ValueError("Item and person must not be empty")
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {
            "item": item,
            "person": person,
            "returned": False
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        res = []
        for key, val in self.data["items"].items():
            res.append({"id": int(key), **val})
        return sorted(res, key=lambda x: x["id"])

    def give_back(self, entry_id):
        key = str(entry_id)
        if key not in self.data["items"]:
            raise ValueError("ID not found")
        if self.data["items"][key]["returned"]:
            raise ValueError("Already returned")
        self.data["items"][key]["returned"] = True
        self._save()

    def remove(self, entry_id):
        key = str(entry_id)
        if key not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][key]
        self._save()

def main():
    args = sys.argv[1:]
    if len(args) < 3:
        sys.stderr.write("Usage: python3 app.py --file PATH COMMAND [ARGS]\n")
        sys.exit(1)
    
    if args[0] != "--file":
        sys.stderr.write("Invalid arguments\n")
        sys.exit(1)
    
    path = args[1]
    cmd = args[2]
    params = args[3:]

    try:
        ll = LoanList(path)
        if cmd == "lend":
            if len(params) < 2: raise ValueError()
            ll.lend(params[0], params[1])
        elif cmd == "list":
            for entry in ll.list():
                suffix = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{suffix}")
        elif cmd == "back":
            if len(params) < 1: raise ValueError()
            ll.give_back(int(params[0]))
        elif cmd == "remove":
            if len(params) < 1: raise ValueError()
            ll.remove(int(params[0]))
        else:
            sys.stderr.write("Unknown command\n")
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(str(e) if str(e) else "Error\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
