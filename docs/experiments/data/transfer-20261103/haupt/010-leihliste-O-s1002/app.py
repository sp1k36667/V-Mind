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
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Damaged JSON file")

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

    def list(self):
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

    def give_back(self, entry_id):
        sid = str(entry_id)
        if sid not in self.data["items"]:
            raise ValueError("ID not found")
        if self.data["items"][sid]["returned"]:
            raise ValueError("Already returned")
        self.data["items"][sid]["returned"] = True
        self._save()

    def remove(self, entry_id):
        sid = str(entry_id)
        if sid not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][sid]
        self._save()

def main():
    args = sys.argv[1:]
    if len(args) < 3 or args[0] != "--file":
        sys.exit(1)
    
    file_path = args[1]
    command = args[2]
    params = args[3:]

    try:
        ll = LoanList(file_path)
        if command == "lend":
            if len(params) != 2: raise ValueError()
            ll.lend(params[0], params[1])
        elif command == "list":
            for entry in ll.list():
                status = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{status}")
        elif command == "back":
            if len(params) != 1: raise ValueError()
            ll.give_back(int(params[0]))
        elif command == "remove":
            if len(params) != 1: raise ValueError()
            ll.remove(int(params[0]))
        else:
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    main()
