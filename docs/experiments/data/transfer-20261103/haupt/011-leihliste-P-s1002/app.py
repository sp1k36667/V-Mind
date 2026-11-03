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
            raise ValueError("Empty fields")
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
            raise ValueError("Not found")
        if self.data["items"][i_str]["returned"]:
            raise ValueError("Already returned")
        self.data["items"][i_str]["returned"] = True
        self._save()

    def remove(self, i_str):
        if not i_str.isdigit():
            raise ValueError("Invalid ID")
        i = int(i_str)
        if i_str not in self.data["items"]:
            raise ValueError("Not found")
        del self.data["items"][i_str]
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
            if len(params) != 2: raise ValueError()
            ll.lend(params[0], params[1])
        elif command == "list":
            for entry in ll.list_items():
                status = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{status}")
        elif command == "back":
            if len(params) != 1: raise ValueError()
            ll.give_back(params[0])
        elif command == "remove":
            if len(params) != 1: raise ValueError()
            ll.remove(params[0])
        else:
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
