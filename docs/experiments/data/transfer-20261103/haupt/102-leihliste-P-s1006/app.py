import json
import sys
import argparse

class LoanList:
    def __init__(self, path):
        self.path = path
        try:
            with open(self.path, 'r') as f:
                data = json.load(f)
                if "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.data = data
        except FileNotFoundError:
            self.data = {"next_id": 1, "items": {}}
        except (json.JSONDecodeError, ValueError):
            raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item.strip() or not person.strip():
            raise ValueError("Empty item or person")
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {
            "item": item,
            "person": person,
            "returned": False
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys())
        result = []
        for i in sorted_ids:
            entry = self.data["items"][i]
            result.append({
                "id": i,
                "item": entry["item"],
                "person": entry["person"],
                "returned": entry["returned"]
            })
        return result

    def give_back(self, entry_id):
        if entry_id not in self.data["items"]:
            raise ValueError("ID not found")
        entry = self.data["items"][entry_id]
        if entry["returned"]:
            raise ValueError("Already returned")
        entry["returned"] = True
        self._save()

    def remove(self, entry_id):
        if entry_id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][entry_id]
        self._save()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("command", choices=["lend", "list", "back", "remove"])
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()

    try:
        ll = LoanList(args.file)
        if args.command == "lend":
            if len(args.args) < 2: raise ValueError("Missing args")
            ll.lend(args.args[0], args.args[1])
        elif args.command == "list":
            for entry in ll.list():
                status = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{status}")
        elif args.command == "back":
            if len(args.args) < 1 or not args.args[0].isdigit(): raise ValueError("ID required")
            ll.give_back(int(args.args[0]))
        elif args.command == "remove":
            if len(args.args) < 1 or not args.args[0].isdigit(): raise ValueError("ID required")
            ll.remove(int(args.args[0]))
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write("Error: " + str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
