import sys
import json
import os

class LoanList:
    def __init__(self, path):
        self.path = path
        self.data = self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return {"next_id": 1, "items": {}}
        try:
            with open(self.path, 'r') as f:
                data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError()
                return data
        except (json.JSONDecodeError, ValueError):
            raise ValueError("Beschädigte oder ungültige Datei.")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def lend(self, item, person):
        if not item or not item.strip():
            raise ValueError("Gegenstand darf nicht leer sein.")
        if not person or not person.strip():
            raise ValueError("Person darf nicht leer sein.")
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {
            "item": item.strip(),
            "person": person.strip(),
            "returned": False
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
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
            raise ValueError("ID nicht gefunden.")
        if self.data["items"][sid]["returned"]:
            raise ValueError("Bereits zurückgegeben.")
        self.data["items"][sid]["returned"] = True
        self._save()

    def remove(self, entry_id):
        sid = str(entry_id)
        if sid not in self.data["items"]:
            raise ValueError("ID nicht gefunden.")
        del self.data["items"][sid]
        self._save()

def main():
    if len(sys.argv) < 3:
        print("Benutzung: python3 app.py --file DATEI BEFEHL [ARGUMENTE]", file=sys.stderr)
        sys.exit(1)
    
    if sys.argv[1] != "--file":
        print("Fehler: Erwarte --file", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[2]
    cmd = sys.argv[3]
    args = sys.argv[4:]

    try:
        ll = LoanList(path)
        if cmd == "lend":
            if len(args) != 2:
                raise ValueError("Erwarte GEGENSTAND und PERSON.")
            ll.lend(args[0], args[1])
        elif cmd == "list":
            for entry in ll.list():
                status = " (zurück)" if entry["returned"] else ""
                print(f"{entry['id']} {entry['item']} an {entry['person']}{status}")
        elif cmd == "back":
            if len(args) != 1 or not args[0].isdigit():
                raise ValueError("Erwarte numerische ID.")
            ll.give_back(int(args[0]))
        elif cmd == "remove":
            if len(args) != 1 or not args[0].isdigit():
                raise ValueError("Erwarte numerische ID.")
            ll.remove(int(args[0]))
        else:
            print("Unbekannter Befehl.", file=sys.stderr)
            sys.exit(1)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Fehler: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
