import sys
import json
import os

class LoanList:
    def __init__(self, path):
        self.path = path
        self.data = self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return {"next_id": 1, "items": {}}
        try:
            with open(self.path, 'r') as f:
                data = json.load(f)
            if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                raise ValueError()
            return data
        except (json.JSONDecodeError, ValueError):
            raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item or not item.strip() or not person or not person.strip():
            raise ValueError()
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {
            "id": new_id,
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
                "id": entry["id"],
                "item": entry["item"],
                "person": entry["person"],
                "returned": entry["returned"]
            })
        return result

    def give_back(self, entry_id):
        if not str(entry_id).isdigit():
            raise ValueError()
        sid = str(entry_id)
        if sid not in self.data["items"]:
            raise ValueError()
        if self.data["items"][sid]["returned"]:
            raise ValueError()
        self.data["items"][sid]["returned"] = True
        self._save()

    def remove(self, entry_id):
        if not str(entry_id).isdigit():
            raise ValueError()
        sid = str(entry_id)
        if sid not in self.data["items"]:
            raise ValueError()
        del self.data["items"][sid]
        self._save()

def main():
    if len(sys.argv) < 4:
        sys.exit(1)
    
    file_path = sys.argv[1]
    command = sys.argv[2]
    args = sys.argv[3:]

    try:
        ll = LoanList(file_path)
        if command == "lend":
            if len(args) < 2: raise ValueError()
            ll.lend(args[0], args[1])
        elif command == "list":
            for item in ll.list_items():
                out = f"{item['id']} {item['item']} an {item['person']}"
                if item['returned']:
                    out += " (zurück)"
                print(out)
        elif command == "back":
            if len(args) < 1: raise ValueError()
            ll.give_back(int(args[0]))
        elif command == "remove":
            if len(args) < 1: raise ValueError()
            ll.remove(int(args[0]))
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
