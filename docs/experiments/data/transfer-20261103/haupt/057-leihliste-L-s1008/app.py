import sys
import json
import os

class LoanList:
    def __init__(self, path):
        self.path = path
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                        raise ValueError("Invalid format")
                    self.data = data
                    # Ensure IDs are handled correctly as strings in JSON but ints in logic
                    self.next_id = data["next_id"]
                    self.items = data["items"]
            except (json.JSONDecodeError, ValueError, KeyError, TypeError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}
            self.next_id = 1
            self.items = {}

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item or not item.strip(): raise ValueError("Item empty")
        if not person or not person.strip(): raise ValueError("Person empty")
        new_id = self.next_id
        self.items[str(new_id)] = {
            "item": item,
            "person": person,
            "returned": False
        }
        self.next_id += 1
        self._save()
        return new_id

    def list_items(self):
        sorted_ids = sorted(self.items.keys(), key=int)
        result = []
        for sid in sorted_ids:
            entry = self.items[sid]
            result.append({
                "id": int(sid),
                "item": entry["item"],
                "person": entry["person"],
                "returned": entry["returned"]
            })
        return result

    def give_back(self, entry_id):
        sid = str(entry_id)
        if sid not in self.items: raise ValueError("Not found")
        if self.items[sid]["returned"]: raise ValueError("Already returned")
        self.items[sid]["returned"] = True
        self._save()

    def remove(self, entry_id):
        sid = str(entry_id)
        if sid not in self.items: raise ValueError("Not found")
        del self.items[sid]
        self._save()

def main():
    if len(sys.argv) < 3:
        sys.stderr.write("Usage: python3 app.py --file PATH COMMAND [ARGS]\n")
        sys.exit(1)
    
    if sys.argv[1] != "--file":
        sys.stderr.write("Usage: python3 app.py --file PATH COMMAND [ARGS]\n")
        sys.exit(1)

    path = sys.argv[2]
    cmd = sys.argv[3]
    args = sys.argv[4:]

    try:
        ll = LoanList(path)
        if cmd == "lend" and len(args) >= 2:
            ll.lend(args[0], args[1])
        elif cmd == "list":
            for entry in ll.list_items():
                status = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{status}")
        elif cmd == "back" and len(args) >= 1:
            ll.give_back(int(args[0]))
        elif cmd == "remove" and len(args) >= 1:
            ll.remove(int(args[0]))
        else:
            sys.stderr.write("Unknown command\n")
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
