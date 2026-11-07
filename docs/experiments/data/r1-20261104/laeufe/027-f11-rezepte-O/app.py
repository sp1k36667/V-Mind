import sys
import json
import os

class RecipeBook:
    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                    if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                        raise ValueError
                    self.data = data
            except (json.JSONDecodeError, ValueError, KeyError):
                raise ValueError("Beschädigte Datei")
        else:
            self.data = {"next_id": 1, "items": {}}
            self.save()

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_minutes(self, minutes):
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError
        return minutes

    def add(self, title, minutes):
        if not title or not title.strip():
            raise ValueError
        minutes = self._validate_minutes(minutes)
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self.save()
        return new_id

    def list(self):
        items = []
        for iid, content in self.data["items"].items():
            if not isinstance(iid, int) or not isinstance(content.get("title"), str) or not isinstance(content.get("minutes"), int):
                raise ValueError
            items.append({"id": iid, "title": content["title"], "minutes": content["minutes"]})
        return sorted(items, key=lambda x: x["id"])

    def set_minutes(self, iid, minutes):
        if iid not in self.data["items"]:
            raise ValueError
        minutes = self._validate_minutes(minutes)
        self.data["items"][iid]["minutes"] = minutes
        self.save()

    def remove(self, iid):
        if iid not in self.data["items"]:
            raise ValueError
        del self.data["items"][iid]
        self.save()

def main():
    try:
        if len(sys.argv) < 3:
            sys.exit(1)
        path = sys.argv[1]
        cmd = sys.argv[2]
        args = sys.argv[3:]
        
        book = RecipeBook(path)
        
        if cmd == "add":
            if len(args) < 2: raise ValueError
            book.add(args[0], int(args[1]))
        elif cmd == "list":
            for item in book.list():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif cmd == "set":
            if len(args) < 2: raise ValueError
            book.set_minutes(int(args[0]), int(args[1]))
        elif cmd == "remove":
            if len(args) < 1: raise ValueError
            book.remove(int(args[0]))
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError, TypeError) as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
