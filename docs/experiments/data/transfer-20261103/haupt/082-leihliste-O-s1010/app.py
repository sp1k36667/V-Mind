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
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item.strip() or not person.strip():
            raise ValueError("Empty item or person")
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {
            "item": item,
            "person": person,
            "returned": False
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list_items(self):
        items = []
        for key, val in self.data["items"].items():
            items.append({"id": int(key), **val})
        return sorted(items, key=lambda x: x["id"])

    def give_back(self, item_id):
        if str(item_id) not in self.data["items"]:
            raise ValueError("Unknown ID")
        entry = self.data["items"][str(item_id)]
        if entry["returned"]:
            raise ValueError("Already returned")
        entry["returned"] = True
        self._save()

    def remove(self, item_id):
        if str(item_id) not in self.data["items"]:
            raise ValueError("Unknown ID")
        del self.data["items"][str(item_id)]
        self._save()

def main():
    try:
        if len(sys.argv) < 4:
            sys.exit(1)
        path = sys.argv[1]
        cmd = sys.argv[2]
        args = sys.argv[3:]
        
        ll = LoanList(path)
        
        if cmd == "lend":
            if len(args) < 2: raise ValueError()
            ll.lend(args[0], args[1])
        elif cmd == "list":
            for item in ll.list_items():
                suffix = " (zurück)" if item["returned"] else ""
                print(f"{item['id']} {item['item']} an {item['person']}{suffix}")
        elif cmd == "back":
            if len(args) < 1: raise ValueError()
            ll.give_back(int(args[0]))
        elif cmd == "remove":
            if len(args) < 1: raise ValueError()
            ll.remove(int(args[0]))
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"{str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
