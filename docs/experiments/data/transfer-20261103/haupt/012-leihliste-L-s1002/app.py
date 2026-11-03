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
                # Convert keys to strings if they aren't already, but we handle them as ints logic-wise
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

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

    def give_back(self, id_val):
        if not str(id_val).isdigit():
            raise ValueError("Invalid ID")
        sid = str(id_val)
        if sid not in self.data["items"]:
            raise ValueError("Not found")
        if self.data["items"][sid]["returned"]:
            raise ValueError("Already returned")
        self.data["items"][sid]["returned"] = True
        self._save()

    def remove(self, id_val):
        if not str(id_val).isdigit():
            raise ValueError("Invalid ID")
        sid = str(id_val)
        if sid not in self.data["items"]:
            raise ValueError("Not found")
        del self.data["items"][sid]
        self._save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        path = args[0]
        cmd = args[1]
        params = args[2:]
        
        ll = LoanList(path)
        
        if cmd == "lend":
            if len(params) < 2: raise ValueError()
            ll.lend(params[0], params[1])
        elif cmd == "list":
            for entry in ll.list():
                status = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{status}")
        elif cmd == "back":
            if len(params) < 1: raise ValueError()
            ll.give_back(params[0])
        elif cmd == "remove":
            if len(params) < 1: raise ValueError()
            ll.remove(params[0])
        else:
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception:
        sys.stderr.write("Error\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
