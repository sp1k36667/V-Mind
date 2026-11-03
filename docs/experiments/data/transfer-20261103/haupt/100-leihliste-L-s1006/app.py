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
                # Convert keys to integers if they are numeric
                for k in self.data["items"]:
                    if k.isdigit():
                        self.data["items"][int(k)] = self.data["items"].pop(k)
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item.strip() or not person.strip():
            raise ValueError("Item and person must be non-empty")
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {
            "item": item,
            "person": person,
            "returned": False
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list_items(self):
        sorted_ids = sorted(self.data["items"].keys())
        result = []
        for idx in sorted_ids:
            entry = self.data["items"][idx]
            result.append({
                "id": idx,
                "item": entry["item"],
                "person": entry["person"],
                "returned": entry["returned"]
            })
        return result

    def give_back(self, entry_id):
        if not isinstance(entry_id, int) or entry_id not in self.data["items"]:
            raise ValueError("Invalid ID")
        entry = self.data["items"][entry_id]
        if entry["returned"]:
            raise ValueError("Already returned")
        entry["returned"] = True
        self._save()

    def remove(self, entry_id):
        if not isinstance(entry_id, int) or entry_id not in self.data["items"]:
            raise ValueError("Invalid ID")
        del self.data["items"][entry_id]
        self._save()

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
            if len(params) < 2: raise ValueError()
            ll.lend(params[0], params[1])
        elif command == "list":
            for entry in ll.list_items():
                ret_str = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{ret_str}")
        elif command == "back":
            if len(params) < 1: raise ValueError()
            ll.give_back(int(params[0]))
        elif command == "remove":
            if len(params) < 1: raise ValueError()
            ll.remove(int(params[0]))
        else:
            sys.exit(1)
            
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
