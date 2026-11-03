import sys
import json
import os

class LoanList:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    self.data = json.load(f)
                    if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                        raise ValueError
                    if not isinstance(self.data["next_id"], int):
                        raise ValueError
                    # Ensure keys are processed correctly
                    self.data["items"] = self.data["items"]
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Beschädigte Datei")

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item.strip() or not person.strip():
            raise ValueError("Leerer Text")
        id_num = self.data["next_id"]
        self.data["items"][str(id_num)] = {
            "item": item,
            "person": person,
            "returned": False
        }
        self.data["next_id"] += 1
        self.save()
        return id_num

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

    def give_back(self, id_num):
        if not str(id_num).isdigit():
            raise ValueError("Ungültige ID")
        sid = str(id_num)
        if sid not in self.data["items"]:
            raise ValueError("Nicht gefunden")
        if self.data["items"][sid]["returned"]:
            raise ValueError("Bereits zurückgegeben")
        self.data["items"][sid]["returned"] = True
        self.save()

    def remove(self, id_num):
        if not str(id_num).isdigit():
            raise ValueError("Ungültige ID")
        sid = str(id_num)
        if sid not in self.data["items"]:
            raise ValueError("Nicht gefunden")
        del self.data["items"][sid]
        self.save()

def main():
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(1)
    
    path = args[0]
    if not path.startswith("--file "):
        # Handle case where first arg is file path directly or with flag
        if args[0].startswith("--file "):
            path = args[0].split("--file ")[1]
            cmd_idx = 2
        else:
            path = args[0]
            cmd_idx = 1
    else:
        cmd_idx = 2

    if cmd_idx >= len(args):
        sys.exit(1)
    
    cmd = args[cmd_idx]
    try:
        ll = LoanList(path)
        if cmd == "lend" and len(args) == cmd_idx + 3:
            ll.lend(args[cmd_idx+1], args[cmd_idx+2])
        elif cmd == "list":
            items = ll.list_items()
            for i in items:
                status = " (zurück)" if i["returned"] else ""
                print(f"{i['id']} {i['item']} an {i['person']}{status}")
        elif cmd == "back" and len(args) == cmd_idx + 2:
            ll.give_back(int(args[cmd_idx+1]))
        elif cmd == "remove" and len(args) == cmd_idx + 2:
            ll.remove(int(args[cmd_idx+1]))
        else:
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write("Fehler\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
