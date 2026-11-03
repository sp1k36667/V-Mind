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
                raise ValueError("Corrupted file")
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
        for k, v in self.data["items"].items():
            items.append({"id": int(k), **v})
        return sorted(items, key=lambda x: x["id"])

    def give_back(self, id_str):
        try:
            idx = int(id_str)
        except ValueError:
            raise ValueError("Invalid ID")
        if str(idx) not in self.data["items"]:
            raise ValueError("Not found")
        entry = self.data["items"][str(idx)]
        if entry["returned"]:
            raise ValueError("Already returned")
        entry["returned"] = True
        self._save()

    def remove(self, id_str):
        try:
            idx = int(id_str)
        except ValueError:
            raise ValueError("Invalid ID")
        if str(idx) not in self.data["items"]:
            raise ValueError("Not found")
        del self.data["items"][str(idx)]
        self._save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        path = args[0]
        command = args[1]
        params = args[2:]

        ll = LoanList(path)

        if command == "lend":
            if len(params) != 2: raise ValueError()
            ll.lend(params[0], params[1])
        elif command == "list":
            for entry in ll.list_items():
                ret = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{ret}")
        elif command == "back":
            if len(params) != 1: raise ValueError()
            ll.give_back(params[0])
        elif command == "remove":
            if len(params) != 1: raise ValueError()
            ll.remove(params[0])
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
