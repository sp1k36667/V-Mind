import sys
import json
import os

class ExpenseLog:
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
                raise ValueError(f"Beschädigte Datei: {path}")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, text, cents):
        if not text or not text.strip():
            raise ValueError("Text darf nicht leer sein.")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Betrag muss eine positive Ganzzahl sein.")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"text": text, "cents": cents}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        items = []
        for iid in sorted(self.data["items"].keys()):
            item = self.data["items"][iid]
            items.append({"id": iid, "text": item["text"], "cents": item["cents"]})
        return items

    def set_cents(self, id, cents):
        if id not in self.data["items"]:
            raise ValueError("ID nicht gefunden.")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Betrag muss eine positive Ganzzahl sein.")
        self.data["items"][id]["cents"] = cents
        self._save()

    def remove(self, id):
        if id not in self.data["items"]:
            raise ValueError("ID nicht gefunden.")
        del self.data["items"][id]
        self._save()

    def total(self):
        return sum(item["cents"] for item in self.data["items"].values())

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        path = args[0]
        cmd = args[1]
        params = args[2:]

        log = ExpenseLog(path)

        if cmd == "add":
            if len(params) < 2: raise ValueError()
            log.add(params[0], int(params[1]))
        elif cmd == "list":
            for item in log.list():
                print(f"{item['id']} {item['cents']} {item['text']}")
        elif cmd == "set":
            if len(params) < 2: raise ValueError()
            log.set_cents(int(params[0]), int(params[1]))
        elif cmd == "remove":
            if len(params) < 1: raise ValueError()
            log.remove(int(params[0]))
        elif cmd == "total":
            print(log.total())
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write("Fehler: " + str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
