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
            raise ValueError("Empty fields")
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
        sorted_ids = sorted(self.data["items"].keys(), key=int)
        result = []
        for sid in sorted_ids:
            entry = self.data["items"][sid]
            result.append({
                "id": entry["id"],
                "item": entry["item"],
                "person": entry["person"],
                "returned": entry["returned"]
            })
        return result

    def give_back(self, id_str):
        if id_str not in self.data["items"]:
            raise ValueError("Unknown ID")
        entry = self.data["items"][id_str]
        if entry["returned"]:
            raise ValueError("Already returned")
        entry["returned"] = True
        self.save()

    def remove(self, id_str):
        if id_str not in self.data["items"]:
            raise ValueError("Unknown ID")
        del self.data["items"][id_str]
        self.save()

def main():
    args = sys.argv[1:]
    if len(args) < 3 or args[0] != "--file":
        sys.exit(1)
    
    path = args[1]
    cmd = args[2]
    params = args[3:]

    try:
        loans = LoanList(path)
        if cmd == "lend":
            if len(params) < 2: raise ValueError("Missing args")
            loans.lend(params[0], params[1])
        elif cmd == "list":
            for item in loans.list_items():
                status = " (zurück)" if item["returned"] else ""
                print(f"{item['id']} {item['item']} an {item['person']}{status}")
        elif cmd == "back":
            if len(params) < 1: raise ValueError("Missing ID")
            loans.give_back(params[0])
        elif cmd == "remove":
            if len(params) < 1: raise ValueError("Missing ID")
            loans.remove(params[0])
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
