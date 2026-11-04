import json
import os

class FilmList:
    """Filmliste, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if not isinstance(loaded, dict) or "next_id" not in loaded or "items" not in loaded:
                        raise ValueError("Invalid format")
                    self.data = loaded
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def _validate_string(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid value")
        return value.strip()

    def add(self, title, director):
        title = self._validate_string(title)
        director = self._validate_string(director)
        
        current_id = self.data["next_id"]
        self.data["items"][current_id] = {
            "title": title,
            "director": director
        }
        self.data["next_id"] += 1
        self._save()
        return current_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys())
        result = []
        for fid in sorted_ids:
            item = self.data["items"][fid]
            result.append({
                "id": fid,
                "title": item["title"],
                "director": item["director"]
            })
        return result

    def set_director(self, id, director):
        if not isinstance(id, int) or id not in self.data["items"]:
            raise ValueError("Invalid ID")
        director = self._validate_string(director)
        self.data["items"][id]["director"] = director
        self._save()

    def remove(self, id):
        if not isinstance(id, int) or id not in self.data["items"]:
            raise ValueError("Invalid ID")
        del self.data["items"][id]
        self._save()
