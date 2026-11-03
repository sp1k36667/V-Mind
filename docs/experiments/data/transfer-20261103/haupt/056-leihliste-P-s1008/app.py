import json
import sys
import argparse
import os

class LoanList:
    def __init__(self, path):
        self.path = path
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2)

    def lend(self, item, person):
        if not item or not item.strip():
            raise ValueError("Empty item")
        if not person or not person.strip():
            raise ValueError("Empty person")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {
            "item": item.strip(),
            "person": person.strip(),
            "returned": False
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list_items(self):
        sorted_ids = sorted(self.data["items"].keys())
        results = []
        for i in sorted_ids:
            entry = self.data["items"][i]
            results.append({
                "id": i,
                "item": entry["item"],
                "person": entry["person"],
                "returned": entry["returned"]
            })
        return results

    def give_back(self, entry_id):
        if not isinstance(entry_id, int) or entry_id not in self.data["items"]:
            raise ValueError("Unknown ID")
        entry = self.data["items"][entry_id]
        if entry["returned"]:
            raise ValueError("Already returned")
        entry["returned"] = True
        self._save()

    def remove(self, entry_id):
        if not isinstance(entry_id, int) or entry_id not in self.data["items"]:
            raise ValueError("Unknown ID")
        del self.data["items"][entry_id]
        self._save()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("command", choices=["lend", "list", "back", "remove"])
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()

    try:
        loan_list = LoanList(args.file)
        if args.command == "lend":
            if len(args.args) != 2:
                raise ValueError("Usage: lend ITEM PERSON")
            loan_list.lend(args.args[0], args.args[1])
        elif args.command == "list":
            for entry in loan_list.list_items():
                suffix = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{suffix}")
        elif args.command == "back":
            if len(args.args) != 1:
                raise ValueError("Usage: back ID")
            loan_list.give_back(int(args.args[0]))
        elif args.command == "remove":
            if len(args.args) != 1:
                raise ValueError("Usage: remove ID")
            loan_list.remove(int(args.args[0]))
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
