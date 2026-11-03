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
                if "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_id(self, id_val):
        if not isinstance(id_val, int) or id_val < 1:
            raise ValueError("Invalid ID")
        if id_val not in self.data["items"] and id_val >= self.data["next_id"]:
            raise ValueError("ID out of range")
        if id_val not in self.data["items"]:
            raise ValueError("ID not found")

    def add(self, title, minutes):
        if not title or title.isspace():
            raise ValueError("Empty title")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"title": title, "minutes": minutes}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list_items(self):
        sorted_ids = sorted(self.data["items"].keys())
        return [{"id": i, **self.data["items"][i]} for i in sorted_ids]

    def set_minutes(self, id_val, minutes):
        self._validate_id(id_val)
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Invalid minutes")
        self.data["items"][id_val]["minutes"] = minutes
        self._save()

    def remove(self, id_val):
        self._validate_id(id_val)
        del self.data["items"][id_val]
        self._save()

def main():
    try:
        args = sys.argv[1:]
        if len(args) < 3:
            sys.exit(1)
        
        file_path = args[0]
        command = args[1]
        book = RecipeBook(file_path)

        if command == "add":
            if len(args) < 4: raise ValueError()
            id_res = book.add(args[2], int(args[3]))
            print(id_res)
        elif command == "list":
            for item in book.list_items():
                print(f"{item['id']} {item['minutes']} min {item['title']}")
        elif command == "set":
            if len(args) < 4: raise ValueError()
            book.set_minutes(int(args[2]), int(args[3]))
        elif command == "remove":
            if len(args) < 3: raise ValueError()
            book.remove(int(args[2]))
        else:
            sys.exit(1)
    except (ValueError, IndexError, KeyError, TypeError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
