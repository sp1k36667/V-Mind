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
                    raise ValueError
                return data
        except (json.JSONDecodeError, ValueError):
            raise ValueError("Datei ist beschädigt oder ungültig.")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item or not item.strip():
            raise ValueError("Item darf nicht leer sein.")
        if not person or not person.strip():
            raise ValueError("Person darf nicht leer sein.")
        
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

    def give_back(self, entry_id):
        sid = str(entry_id)
        if sid not in self.data["items"]:
            raise ValueError("ID unbekannt.")
        entry = self.data["items"][sid]
        if entry["returned"]:
            raise ValueError("Bereits zurückgegeben.")
        entry["returned"] = True
        self._save()

    def remove(self, entry_id):
        sid = str(entry_id)
        if sid not in self.data["items"]:
            raise ValueError("ID unbekannt.")
        del self.data["items"][sid]
        self._save()

def main():
    if len(sys.argv) < 4:
        sys.exit(1)
    
    path = sys.argv[1]
    cmd = sys.argv[2]
    args = sys.argv[3:]

    try:
        ll = LoanList(path)
        if cmd == "lend" and len(args) == 2:
            ll.lend(args[0], args[1])
        elif cmd == "list":
            for item in ll.list_items():
                suffix = " (zurück)" if item["returned"] else ""
                print(f"{item['id']} {item['item']} an {item['person']}{suffix}")
        elif cmd == "back" and len(args) == 1:
            ll.give_back(int(args[0]))
        elif cmd == "remove" and len(args) == 1:
            ll.remove(int(args[0]))
        else:
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write("Fehler: " + str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
