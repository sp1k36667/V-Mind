import json
import sys
import argparse

class LoanList:
    def __init__(self, path):
        self.path = path
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                if "next_id" not in data or "items" not in data:
                    raise ValueError
                self.data = data
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            self.data = {"next_id": 1, "items": {}}
            self.save()

    def save(self):
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
            raise ValueError
        if self.data["items"][sid]["returned"]:
            raise ValueError
        self.data["items"][sid]["returned"] = True
        self.save()

    def remove(self, entry_id):
        sid = str(entry_id)
        if sid not in self.data["items"]:
            raise ValueError
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
                raise ValueError
            ll.lend(args.args[0], args.args[1])
        elif args.command == "list":
            items = ll.list_items()
            for i in items:
                status = " (zurück)" if i["returned"] else ""
                print(f"{i['id']} {i['item']} an {i['person']}{status}")
        elif args.command == "back":
            if len(args.args) < 1:
                raise ValueError
            ll.give_back(int(args.args[0]))
        elif args.command == "remove":
            if len(args.args) < 1:
                raise ValueError
            ll.remove(int(args.args[0]))
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
