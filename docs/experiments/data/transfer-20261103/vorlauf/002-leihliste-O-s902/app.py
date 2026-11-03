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
        self.save()

    def save(self):
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
        self.save()
        return new_id

    def list_items(self):
        items = []
        for idx, val in sorted(self.data["items"].items(), key=lambda x: int(x[0])):
            items.append({
                "id": int(idx),
                "item": val["item"],
                "person": val["person"],
                "returned": val["returned"]
            })
        return items

    def give_back(self, item_id):
        if str(item_id) not in self.data["items"]:
            raise ValueError("ID not found")
        entry = self.data["items"][str(item_id)]
        if entry["returned"]:
            raise ValueError("Already returned")
        entry["returned"] = True
        self.save()

    def remove(self, item_id):
        if str(item_id) not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(item_id)]
        self.save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        file_path = args[0]
        command = args[1]
        params = args[2:]
        
        ll = LoanList(file_path)
        
        if command == "lend":
            if len(params) != 2: raise ValueError()
            ll.lend(params[0], params[1])
        elif command == "list":
            for entry in ll.list_items():
                status = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{status}")
        elif command == "back":
            if len(params) != 1: raise ValueError()
            ll.give_back(int(params[0]))
        elif command == "remove":
            if len(params) != 1: raise ValueError()
            ll.remove(int(params[0]))
        else:
            pass
    except Exception as e:
        sys.stderr.write(f"{str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
