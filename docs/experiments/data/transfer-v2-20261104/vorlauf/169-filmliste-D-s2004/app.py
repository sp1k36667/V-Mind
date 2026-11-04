import json
import os

class FilmList:
    """Filmliste, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.next_id = data["next_id"]
                self.items = {int(k): v for k, v in data["items"].items()}
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Damaged JSON file")
        else:
            self.next_id = 1
            self.items = {}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({"next_id": self.next_id, "items": self.items}, f)

    def _validate_strings(self, *args):
        for arg in args:
            if not isinstance(arg, str) or not arg.strip():
                raise ValueError("Invalid input")

    def add(self, title, director):
        self._validate_strings(title, director)
        new_id = self.next_id
        self.items[new_id] = {"title": title, "director": director}
        self.next_id += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.items.keys())
        return [{"id": i, "title": self.items[i]["title"], "director": self.items[i]["director"]} for i in sorted_ids]

    def set_director(self, id, director):
        self._validate_strings(director)
        if not isinstance(id, int) or id not in self.items:
            raise ValueError("ID not found")
        self.items[id]["director"] = director
        self._save()

    def remove(self, id):
        if not isinstance(id, int) or id not in self.items:
            raise ValueError("ID not found")
        del self.items[id]
        self._save()
