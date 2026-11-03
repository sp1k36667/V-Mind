import json
import sys
import argparse
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
                raise ValueError("Damaged JSON file")
        self.save()

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item or not item.strip():
            raise ValueError("Empty item")
        if not person or not person.strip():
            raise ValueError("Empty person")
        
        item = item.strip()
        person = person.strip()
        
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
            raise ValueError("Unknown ID")
        entry = self.data["items"][sid]
        if entry["returned"]:
            raise ValueError("Already returned")
        entry["returned"] = True
        self.save()

    def remove(self, entry_id):
        sid = str(entry_id)
        if sid not in self.data["items"]:
            raise ValueError("Unknown ID")
        del self.data["items"][sid]
        self.save()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("command", choices=["lend", "list", "back", "remove"])
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()

    try:
        ll = LoanList(args.file)
        if args.command == "lend":
            if len(args.args) < 2:
                raise ValueError("Missing args")
            ll.lend(args.args[0], args.args[1])
        elif args.command == "list":
            items = ll.list_items()
            for i in items:
                line = f"{i['id']} {i['item']} an {i['person']}"
                if i['returned']:
                    line += " (zurück)"
                print(line)
        elif args.command == "back":
            if len(args.args) < 1:
                raise ValueError("Missing ID")
            ll.give_back(int(args.args[0]))
        elif args.command == "remove":
            if len(args.args) < 1:
                raise ValueError("Missing ID")
            ll.remove(int(args.args[0]))
    except (ValueError, IndexError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
