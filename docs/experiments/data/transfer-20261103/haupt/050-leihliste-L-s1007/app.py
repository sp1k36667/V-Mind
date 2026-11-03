import sys
import json
import os

class LoanList:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    content = json.load(f)
                    if not isinstance(content, dict) or "next_id" not in content or "items" not in content:
                        raise ValueError
                    self.data = content
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Beschädigte Datei")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item.strip() or not person.strip():
            raise ValueError
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

    def give_back(self, item_id):
        try:
            sid = str(item_id)
            if sid not in self.data["items"]:
                raise ValueError
            entry = self.data["items"][sid]
            if entry["returned"]:
                raise ValueError
            entry["returned"] = True
            self._save()
        except ValueError:
            raise ValueError

    def remove(self, item_id):
        sid = str(item_id)
        if sid not in self.data["items"]:
            raise ValueError
        del self.data["items"][sid]
        self._save()

def main():
    args = sys.argv[1:]
    if len(args) < 3:
        sys.exit(1)
    
    file_path = args[0]
    command = args[1]
    params = args[2:]

    try:
        ll = LoanList(file_path)
        if command == "lend":
            if len(params) != 2: raise ValueError
            ll.lend(params[0], params[1])
        elif command == "list":
            for entry in ll.list_items():
                status = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{status}")
        elif command == "back":
            if len(params) != 1: raise ValueError
            ll.give_back(int(params[0]))
        elif command == "remove":
            if len(params) != 1: raise ValueError
            ll.remove(int(params[0]))
        else:
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
