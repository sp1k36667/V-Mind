import sys
import json
import os

class LoanList:
    def __init__(self, path):
        self.path = path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                    if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                        raise ValueError()
                    return data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Beschädigte Datei")
        return {"next_id": 1, "items": {}}

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item.strip() or not person.strip():
            raise ValueError("Leere Felder")
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {
            "item": item,
            "person": person,
            "returned": False
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list_items(self):
        res = []
        for iid in sorted(self.data["items"].keys()):
            entry = self.data["items"][iid]
            res.append({
                "id": iid,
                "item": entry["item"],
                "person": entry["person"],
                "returned": entry["returned"]
            })
        return res

    def give_back(self, iid):
        if iid not in self.data["items"]:
            raise ValueError("Nicht gefunden")
        if self.data["items"][iid]["returned"]:
            raise ValueError("Bereits zurückgegeben")
        self.data["items"][iid]["returned"] = True
        self._save()

    def remove(self, iid):
        if iid not in self.data["items"]:
            raise ValueError("Nicht gefunden")
        del self.data["items"][iid]
        self._save()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("command", choices=["lend", "list", "back", "remove"])
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()

    try:
        ll = LoanList(args.file)
        if args.command == "lend":
            if len(args.args) < 2: raise ValueError()
            ll.lend(args.args[0], args.args[1])
        elif args.command == "list":
            for entry in ll.list_items():
                status = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{status}")
        elif args.command == "back":
            if len(args.args) < 1 or not args.args[0].isdigit(): raise ValueError()
            ll.give_back(int(args.args[0]))
        elif args.command == "remove":
            if len(args.args) < 1 or not args.args[0].isdigit(): raise ValueError()
            ll.remove(int(args.args[0]))
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)
