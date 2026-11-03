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
                    raise ValueError
                self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("File is corrupted.")
        else:
            self.data = {"next_id": 1, "items": {}}
        self.save()

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item.strip() or not person.strip():
            raise ValueError
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {
            "id": new_id,
            "item": item,
            "person": person,
            "returned": False
        }
        self.data["next_id"] += 1
        self.save()
        return new_id

    def list_items(self):
        items = []
        for k, v in self.data["items"].items():
            items.append(v)
        return sorted(items, key=lambda x: x["id"])

    def give_back(self, id_str):
        if id_str not in self.data["items"]:
            raise ValueError
        entry = self.data["items"][id_str]
        if entry["returned"]:
            raise ValueError
        entry["returned"] = True
        self.save()

    def remove(self, id_str):
        if id_str not in self.data["items"]:
            raise ValueError
        del self.data["items"][id_str]
        self.save()

def main():
    if len(sys.argv) < 3:
        sys.exit(1)
    
    path = sys.argv[1]
    cmd = sys.argv[2]
    try:
        ll = LoanList(path)
        if cmd == "lend":
            if len(sys.argv) < 5: sys.exit(1)
            ll.lend(sys.argv[3], sys.argv[4])
        elif cmd == "list":
            for entry in ll.list_items():
                res = f"{entry['id']} {entry['item']} an {entry['person']}"
                if entry['returned']:
                    res += " (zurück)"
                print(res)
        elif cmd == "back":
            if len(sys.argv) < 4: sys.exit(1)
            ll.give_back(sys.argv[3])
        elif cmd == "remove":
            if len(sys.argv) < 4: sys.exit(1)
            ll.remove(sys.argv[3])
        else:
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write("Error: " + str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
