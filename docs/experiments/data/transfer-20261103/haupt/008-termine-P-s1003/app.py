import sys
import json
import os
import re

def validate_date(date_str):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise ValueError("Ungültiges Datumsformat. Erwartet: JJJJ-MM-TT.")
    try:
        # Prüfen, ob Datum existiert (z.B. kein 31. Feb)
        year, month, day = map(int, date_str.split("-"))
        import datetime
        datetime.date(year, month, day)
    except ValueError:
        raise ValueError("Ungültiges Datum.")

class Calendar:
    def __init__(self, path):
        self.path = path
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError()
                self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Beschädigte Datei.")
        else:
            self.data = {"next_id": 1, "items": {}}
        self.save()

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, title, date):
        if not title or title.isspace():
            raise ValueError("Titel darf nicht leer sein.")
        validate_date(date)
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"title": title, "date": date}
        self.data["next_id"] += 1
        self.save()
        return new_id

    def list(self):
        items = []
        for k, v in self.data["items"].items():
            items.append({"id": int(k), **v})
        items.sort(key=lambda x: (x["date"], x["id"]))
        return items

    def move(self, id_str, date):
        if id_str not in self.data["items"]:
            raise ValueError("ID nicht gefunden.")
        validate_date(date)
        self.data["items"][id_str]["date"] = date
        self.save()

    def remove(self, id_str):
        if id_str not in self.data["items"]:
            raise ValueError("ID nicht gefunden.")
        del self.data["items"][id_str]
        self.save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        path = args[0]
        cmd = args[1]
        cal = Calendar(path)

        if cmd == "add":
            if len(args) < 4: raise ValueError()
            cal.add(args[2], args[3])
        elif cmd == "list":
            for item in cal.list():
                print(f"{item['id']} {item['date']} {item['title']}")
        elif cmd == "move":
            if len(args) < 4: raise ValueError()
            cal.move(args[2], args[3])
        elif cmd == "remove":
            if len(args) < 3: raise ValueError()
            cal.remove(args[2])
        else:
            sys.exit(1)
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
