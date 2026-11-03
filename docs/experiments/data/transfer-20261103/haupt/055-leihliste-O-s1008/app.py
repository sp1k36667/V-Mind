import json
import sys
import os

class LoanList:
    def __init__(self, path):
        self.path = path
        self.data = None
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    self.data = json.load(f)
                if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                    raise ValueError("Invalid format")
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}

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
        sorted_ids = sorted(self.data["items"].keys(), key=int)
        result = []
        for sid in sorted_ids:
            entry = self.data["items"][sid]
            result.append({
                "id": int(sid),
                "item": entry["item"],
                "person": entry["person"],
                "returned": entry["returned"]
            })
        return result

    def give_back(self, lid):
        try:
            lid = int(lid)
            if str(lid) not in self.data["items"]:
                raise ValueError()
            entry = self.data["items"][str(lid)]
            if entry["returned"]:
                raise ValueError("Already returned")
            entry["returned"] = True
            self.save()
        except ValueError:
            raise ValueError("Invalid ID or already returned")

    def remove(self, lid):
        try:
            lid = int(lid)
            if str(lid) not in self.data["items"]:
                raise ValueError()
            del self.data["items"][str(lid)]
            self.save()
        except ValueError:
            raise ValueError("Invalid ID")

def main():
    if len(sys.argv) < 4:
        sys.exit(1)
    
    path = sys.argv[1]
    cmd = sys.argv[2]
    args = sys.argv[3:]

    try:
        ll = LoanList(path)
        if cmd == "lend":
            if len(args) < 2: raise ValueError()
            ll.lend(args[0], args[1])
        elif cmd == "list":
            for item in ll.list_items():
                status = " (zurück)" if item["returned"] else ""
                print(f"{item['id']} {item['item']} an {item['person']}{status}")
        elif cmd == "back":
            ll.give_back(args[0])
        elif cmd == "remove":
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
