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
        idx = self.data["next_id"]
        self.data["items"][idx] = {
            "item": item,
            "person": person,
            "returned": False
        }
        self.data["next_id"] += 1
        self._save()
        return idx

    def list_items(self):
        res = []
        for k, v in self.data["items"].items():
            res.append({"id": k, **v})
        return sorted(res, key=lambda x: x["id"])

    def give_back(self, idx):
        if not isinstance(idx, int) or idx not in self.data["items"]:
            raise ValueError("Invalid ID")
        entry = self.data["items"][idx]
        if entry["returned"]:
            raise ValueError("Already returned")
        entry["returned"] = True
        self._save()

    def remove(self, idx):
        if not isinstance(idx, int) or idx not in self.data["items"]:
            raise ValueError("Invalid ID")
        del self.data["items"][idx]
        self._save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 2:
            sys.exit(1)
        
        path = args[0]
        cmd = args[1]
        
        ll = LoanList(path)
        
        if cmd == "lend" and len(args) == 4:
            ll.lend(args[2], args[3])
        elif cmd == "list":
            for item in ll.list_items():
                ret_str = " (zurück)" if item["returned"] else ""
                print(f"{item['id']} {item['item']} an {item['person']}{ret_str}")
        elif cmd == "back" and len(args) == 3:
            ll.give_back(int(args[2]))
        elif cmd == "remove" and len(args) == 3:
            ll.remove(int(args[2]))
        else:
            sys.exit(1)
            
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception:
        sys.stderr.write("Error\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
