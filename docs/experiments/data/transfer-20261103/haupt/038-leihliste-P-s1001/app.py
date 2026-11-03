import sys
import json
import os

class LoanList:
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

    def lend(self, item, person):
        if not item.strip() or not person.strip():
            raise ValueError("Empty values")
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
        results = []
        for k, v in self.data["items"].items():
            results.append({"id": int(k), **v})
        return sorted(results, key=lambda x: x["id"])

    def give_back(self, entry_id):
        if str(entry_id) not in self.data["items"]:
            raise ValueError("ID not found")
        item = self.data["items"][str(entry_id)]
        if item["returned"]:
            raise ValueError("Already returned")
        item["returned"] = True
        self._save()

    def remove(self, entry_id):
        if str(entry_id) not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(entry_id)]
        self._save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            print("Usage: python3 app.py --file PATH COMMAND [ARGS]", file=sys.stderr)
            sys.exit(1)
        
        path = args[1]
        if not path.startswith("--file "):
            path = args[1].split("--file ")[1]
        
        # Simple parser for --file PATH COMMAND
        if "--file" in args:
            idx = args.index("--file")
            path = args[idx+1]
            cmd = args[idx+2]
            params = args[idx+3:]
        else:
            path = args[0]
            cmd = args[1]
            params = args[2:]

        ll = LoanList(path)

        if cmd == "lend":
            if len(params) < 2: raise ValueError("Missing args")
            ll.lend(params[0], params[1])
        elif cmd == "list":
            for entry in ll.list():
                res = f"{entry['id']} {entry['item']} an {entry['person']}"
                if entry['returned']:
                    res += " (zurück)"
                print(res)
        elif cmd == "back":
            if len(params) < 1: raise ValueError("Missing ID")
            ll.give_back(int(params[0]))
        elif cmd == "remove":
            if len(params) < 1: raise ValueError("Missing ID")
            ll.remove(int(params[0]))
        else:
            print("Unknown command", file=sys.stderr)
            sys.exit(1)

    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
