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
                        raise ValueError("Invalid format")
            except Exception:
                raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item.strip() or not person.strip():
            raise ValueError("Empty item or person")
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {
            "id": new_id,
            "item": item,
            "person": person,
            "returned": False
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list_items(self):
        sorted_ids = sorted(self.data["items"].keys(), key=int)
        return [{"id": int(k), **self.data["items"][k]} for k in sorted_ids]

    def give_back(self, lid):
        if str(lid) not in self.data["items"]:
            raise ValueError("Unknown ID")
        entry = self.data["items"][str(lid)]
        if entry["returned"]:
            raise ValueError("Already returned")
        entry["returned"] = True
        self._save()

    def remove(self, lid):
        if str(lid) not in self.data["items"]:
            raise ValueError("Unknown ID")
        del self.data["items"][str(lid)]
        self._save()

def main():
    args = sys.argv[1:]
    if len(args) < 3 or args[0] != "--file":
        sys.exit(1)
    
    path = args[1]
    cmd = args[2]
    
    try:
        ll = LoanList(path)
        if cmd == "lend":
            if len(args) < 5: raise ValueError("Missing args")
            ll.lend(args[3], args[4])
        elif cmd == "list":
            for x in ll.list_items():
                ret = " (zurück)" if x["returned"] else ""
                print(f"{x['id']} {x['item']} an {x['person']}{ret}")
        elif cmd == "back":
            if len(args) < 4: raise ValueError("Missing ID")
            ll.give_back(int(args[3]))
        elif cmd == "remove":
            if len(args) < 4: raise ValueError("Missing ID")
            ll.remove(int(args[3]))
        else:
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
