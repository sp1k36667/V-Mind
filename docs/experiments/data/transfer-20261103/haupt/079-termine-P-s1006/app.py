import sys
import json
import os
import re

class Calendar:
    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    self.data = json.load(f)
                    if not isinstance(self.data.get("next_id"), int) or \
                       not isinstance(self.data.get("items"), dict):
                        raise ValueError
                # Sicherstellen, dass next_id die höchste ID + 1 ist
                if self.data["items"]:
                    max_id = max(self.data["items"].keys())
                    if max_id >= self.data["next_id"]:
                        self.data["next_id"] = max_id + 1
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Beschädigte Datei")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_date(self, date_str):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            raise ValueError("Ungültiges Datum")
        try:
            # Prüft ob Datum existiert (z.B. kein 31. Feb)
            import datetime
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Ungültiges Datum")

    def add(self, title, date):
        if not title or title.isspace():
            raise ValueError("Titel darf nicht leer sein")
        self._validate_date(date)
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"title": title, "date": date}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        items = []
        for i_id, content in self.data["items"].items():
            items.append({"id": i_id, "title": content["title"], "date": content["date"]})
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, i_id, date):
        if i_id not in self.data["items"]:
            raise ValueError("ID nicht gefunden")
        self._validate_date(date)
        self.data["items"][i_id]["date"] = date
        self._save()

    def remove(self, i_id):
        if i_id not in self.data["items"]:
            raise ValueError("ID nicht gefunden")
        del self.data["items"][i_id]
        self._save()

def main():
    if len(sys.argv) < 3:
        sys.exit(1)
    
    path = sys.argv[1]
    cmd = sys.argv[2]
    args = sys.argv[3:]

    try:
        cal = Calendar(path)
        if cmd == "add" and len(args) == 2:
            cal.add(args[0], args[1])
        elif cmd == "list":
            for item in cal.list():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif cmd == "move" and len(args) == 2:
            cal.move(int(args[0]), args[1])
        elif cmd == "remove" and len(args) == 1:
            cal.remove(int(args[0]))
        else:
            sys.exit(1)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write("Fehler: " + str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
