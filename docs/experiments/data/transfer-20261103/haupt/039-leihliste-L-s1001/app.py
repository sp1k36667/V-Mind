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
                    loaded = json.load(f)
                    if not isinstance(loaded, dict) or "next_id" not in loaded or "items" not in loaded:
                        raise ValueError("Invalid format")
                    self.data = loaded
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Damaged file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item or not item.strip(): raise ValueError()
        if not person or not person.strip(): raise ValueError()
        item = item.strip()
        person = person.strip()
        
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
        for k, v in self.data["items"].items():
            items.append({"id": int(k), **v})
        return sorted(items, key=lambda x: x["id"])

    def give_back(self, id_str):
        try:
            idx = int(id_str)
        except ValueError:
            raise ValueError()
        
        if str(idx) not in self.data["items"]:
            raise ValueError()
        
        entry = self.data["items"][str(idx)]
        if entry["returned"]:
            raise ValueError()
        
        entry["returned"] = True
        self._save()

    def remove(self, id_str):
        try:
            idx = int(id_str)
        except ValueError:
            raise ValueError()
        
        if str(idx) not in self.data["items"]:
            raise ValueError()
        
        del self.data["items"][str(idx)]
        self._save()

def main():
    if len(sys.argv) < 4 or sys.argv[1] != "--file":
        sys.exit(1)
    
    path = sys.argv[2]
    cmd = sys.argv[3]
    args = sys.argv[4:]

    try:
        ll = LoanList(path)
        if cmd == "lend":
            if len(args) != 2: raise ValueError()
            ll.lend(args[0], args[1])
        elif cmd == "list":
            for entry in ll.list_items():
                suffix = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{suffix}")
        elif cmd == "back":
            if len(args) != 1: raise ValueError()
            ll.give_back(args[0])
        elif cmd == "remove":
            if len(args) != 1: raise ValueError()
            ll.remove(args[0])
        else:
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
