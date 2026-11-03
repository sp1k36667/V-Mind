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
                        raise ValueError
                    self.data = data
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Damaged JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item or not item.strip():
            raise ValueError("Item cannot be empty")
        if not person or not person.strip():
            raise ValueError("Person cannot be empty")
        
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
        items = []
        for key, val in self.data["items"].items():
            items.append({
                "id": int(key),
                "item": val["item"],
                "person": val["person"],
                "returned": val["returned"]
            })
        return sorted(items, key=lambda x: x["id"])

    def give_back(self, entry_id):
        key = str(entry_id)
        if key not in self.data["items"]:
            raise ValueError("ID not found")
        if self.data["items"][key]["returned"]:
            raise ValueError("Already returned")
        self.data["items"][key]["returned"] = True
        self._save()

    def remove(self, entry_id):
        key = str(entry_id)
        if key not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][key]
        self._save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        
        file_path = args[1]
        command = args[2].lower()
        
        loan_list = LoanList(file_path)
        
        if command == "lend":
            if len(args) < 5:
                sys.exit(1)
            loan_list.lend(args[3], args[4])
        elif command == "list":
            for entry in loan_list.list_items():
                ret_str = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{ret_str}")
        elif command == "back":
            if len(args) < 4:
                sys.exit(1)
            loan_list.give_back(int(args[3]))
        elif command == "remove":
            if len(args) < 4:
                sys.exit(1)
            loan_list.remove(int(args[3]))
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
