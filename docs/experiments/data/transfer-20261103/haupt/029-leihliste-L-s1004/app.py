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
                    content = json.load(f)
                    if not isinstance(content, dict) or "next_id" not in content or "items" not in content:
                        raise ValueError
                    self.data = content
            except (json.JSONDecodeError, ValueError):
                raise ValueError(f"Error reading {path}")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item.strip() or not person.strip():
            raise ValueError("Item and person must not be empty.")
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
        for i_str in sorted_ids:
            i = int(i_str)
            entry = self.data["items"][i_str]
            result.append({
                "id": i,
                "item": entry["item"],
                "person": entry["person"],
                "returned": entry["returned"]
            })
        return result

    def give_back(self, i_str):
        if not i_str.isdigit():
            raise ValueError("Invalid ID")
        i = int(i_str)
        if i_str not in self.data["items"]:
            raise ValueError("ID not found")
        entry = self.data["items"][i_str]
        if entry["returned"]:
            raise ValueError("Already returned")
        entry["returned"] = True
        self._save()

    def remove(self, i_str):
        if not i_str.isdigit():
            raise ValueError("Invalid ID")
        i = int(i_str)
        if i_str not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][i_str]
        self._save()

def main():
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(1)
    
    path = args[0]
    cmd = args[1]
    
    try:
        ll = LoanList(path)
        if cmd == "lend":
            if len(args) < 4: raise ValueError()
            ll.lend(args[2], args[3])
        elif cmd == "list":
            for entry in ll.list():
                ret_str = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{ret_str}")
        elif cmd == "back":
            if len(args) < 3: raise ValueError()
            ll.give_back(args[2])
        elif cmd == "remove":
            if len(args) < 3: raise ValueError()
            ll.remove(args[2])
        else:
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Unexpected error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
