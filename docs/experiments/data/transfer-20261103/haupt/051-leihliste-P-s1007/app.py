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
                    self.data = json.load(f)
                if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                    raise ValueError
            except (json.JSONDecodeError, ValueError):
                raise ValueError(f"File {path} is corrupted.")

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

    def give_back(self, id_str):
        if not str(id_str).isdigit():
            raise ValueError("Invalid ID.")
        id_int = int(id_str)
        if id_str not in self.data["items"]:
            raise ValueError("ID not found.")
        if self.data["items"][id_str]["returned"]:
            raise ValueError("Item already returned.")
        self.data["items"][id_str]["returned"] = True
        self._save()

    def remove(self, id_str):
        if not str(id_str).isdigit():
            raise ValueError("Invalid ID.")
        id_int = int(id_str)
        if id_str not in self.data["items"]:
            raise ValueError("ID not found.")
        del self.data["items"][id_str]
        self._save()

def main():
    if len(sys.argv) < 4 or sys.argv[1] != "--file":
        sys.exit(1)
    
    path = sys.argv[2]
    try:
        ll = LoanList(path)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

    cmd = sys.argv[3]
    args = sys.argv[4:]

    try:
        if cmd == "lend" and len(args) == 2:
            ll.lend(args[0], args[1])
        elif cmd == "list":
            for entry in ll.list_items():
                status = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{status}")
        elif cmd == "back" and len(args) == 1:
            ll.give_back(args[0])
        elif cmd == "remove" and len(args) == 1:
            ll.remove(args[0])
        else:
            sys.stderr.write("Invalid command or arguments.\n")
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
