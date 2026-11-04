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
                self.data = data
                # Convert keys to int
                new_items = {}
                for k, v in data["items"].items():
                    new_items[int(k)] = v
                self.data["items"] = new_items
            except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                raise ValueError("Damaged or invalid JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}
            self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)

    def _validate_string(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid input")
        return value.strip()

    def add(self, title, director):
        t = self._validate_string(title)
        d = self._validate_string(director)
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"title": t, "director": d}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys())
        result = []
        for i in sorted_ids:
            item = self.data["items"][i]
            result.append({"id": i, "title": item["title"], "director": item["director"]})
        return result

    def set_director(self, id, director):
        try:
            idx = int(id)
        except (ValueError, TypeError):
            raise ValueError("Invalid ID")
        if idx not in self.data["items"]:
            raise ValueError("ID not found")
        d = self._validate_string(director)
        self.data["items"][idx]["director"] = d
        self._save()

    def remove(self, id):
        try:
            idx = int(id)
        except (ValueError, TypeError):
            raise ValueError("Invalid ID")
        if idx not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][idx]
        self._save()
