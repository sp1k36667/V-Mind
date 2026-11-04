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
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def _validate_string(self, val):
        if not isinstance(val, str) or not val.strip():
            raise ValueError("Invalid input")
        return val.strip()

    def add(self, title, director):
        title = self._validate_string(title)
        director = self._validate_string(director)
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {
            "title": title,
            "director": director
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        result = []
        for key, val in self.data["items"].items():
            result.append({
                "id": int(key),
                "title": val["title"],
                "director": val["director"]
            })
        return sorted(result, key=lambda x: x["id"])

    def set_director(self, id, director):
        id_str = str(id)
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        director = self._validate_string(director)
        self.data["items"][id_str]["director"] = director
        self._save()

    def remove(self, id):
        id_str = str(id)
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id_str]
        self._save()
