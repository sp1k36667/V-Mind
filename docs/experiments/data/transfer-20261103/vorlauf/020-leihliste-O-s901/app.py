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
        self.save()

    def save(self):
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
        self.save()
        return new_id

    def list_items(self):
        sorted_ids = sorted(self.data["items"].keys(), key=int)
        result = []
        for idx in sorted_ids:
            entry = self.data["items"][idx]
            result.append({
                "id": int(idx),
                "item": entry["item"],
                "person": entry["person"],
                "returned": entry["returned"]
            })
        return result

    def give_back(self, entry_id):
        s_id = str(entry_id)
        if s_id not in self.data["items"]:
            raise ValueError("ID not found")
        if self.data["items"][s_id]["returned"]:
            raise ValueError("Already returned")
        self.data["items"][s_id]["returned"] = True
        self.save()

    def remove(self, entry_id):
        s_id = str(entry_id)
        if s_id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][s_id]
        self.save()

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
            for entry in ll.list_items():
                status = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{status}")
        elif command == "back":
            ll.give_back(int(args[0]))
        elif command == "remove":
            ll.remove(int(args[0]))
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
