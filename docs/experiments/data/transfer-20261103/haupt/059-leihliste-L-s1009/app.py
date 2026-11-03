import sys
import json
import os

class LoanList:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    self.data = json.load(f)
                if not isinstance(self.data.get("next_id"), int) or \
                   not isinstance(self.data.get("items"), dict):
                    raise ValueError("Invalid format")
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted JSON file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item.strip() or not person.strip():
            raise ValueError("Item and person must not be empty")
        
        idx = self.data["next_id"]
        self.data["items"][str(idx)] = {
            "item": item,
            "person": person,
            "returned": False
        }
        self.data["next_id"] += 1
        self._save()
        return idx

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

    def give_back(self, idx):
        if str(idx) not in self.data["items"]:
            raise ValueError("ID not found")
        entry = self.data["items"][str(idx)]
        if entry["returned"]:
            raise ValueError("Already returned")
        entry["returned"] = True
        self._save()

    def remove(self, idx):
        if str(idx) not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(idx)]
        self._save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 2:
            return
        
        file_path = args[0]
        cmd = args[1]
        ll = LoanList(file_path)

        if cmd == "lend":
            if len(args) < 4: raise ValueError("Missing args")
            ll.lend(args[2], args[3])
        elif cmd == "list":
            for item in ll.list_items():
                status = " (zurück)" if item["returned"] else ""
                print(f"{item['id']} {item['item']} an {item['person']}{status}")
        elif cmd == "back":
            if len(args) < 3: raise ValueError("Missing ID")
            ll.give_back(int(args[2]))
        elif cmd == "remove":
            if len(args) < 3: raise ValueError("Missing ID")
            ll.remove(int(args[2]))
        else:
            print("Unknown command")
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
