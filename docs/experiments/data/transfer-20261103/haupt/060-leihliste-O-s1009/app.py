import sys
import json
import os

class LoanList:
    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                if "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item.strip() or not person.strip():
            raise ValueError("Empty fields")
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {
            "item": item.strip(),
            "person": person.strip(),
            "returned": False
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list_items(self):
        res = []
        for iid in sorted(self.data["items"].keys()):
            val = self.data["items"][iid]
            res.append({
                "id": iid,
                "item": val["item"],
                "person": val["person"],
                "returned": val["returned"]
            })
        return res

    def give_back(self, iid):
        if iid not in self.data["items"]:
            raise ValueError("ID not found")
        if self.data["items"][iid]["returned"]:
            raise ValueError("Already returned")
        self.data["items"][iid]["returned"] = True
        self._save()

    def remove(self, iid):
        if iid not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][iid]
        self._save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        path = args[0]
        cmd = args[1]
        params = args[2:]
        
        ll = LoanList(path)
        
        if cmd == "lend":
            if len(params) < 2: raise ValueError()
            ll.lend(params[0], params[1])
        elif cmd == "list":
            for entry in ll.list_items():
                ret_str = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{ret_str}")
        elif cmd == "back":
            if len(params) < 1: raise ValueError()
            ll.give_back(int(params[0]))
        elif cmd == "remove":
            if len(params) < 1: raise ValueError()
            ll.remove(int(params[0]))
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
