import json
import os

class FilmList:
    """Filmliste, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    if not isinstance(content, dict) or "next_id" not in content or "items" not in content:
                        raise ValueError("Invalid format")
                    self.data = content
                    # Ensure keys are integers
                    new_items = {}
                    for k, v in content["items"].items():
                        new_items[int(k)] = v
                    self.data["items"] = new_items
            except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                raise ValueError("Corrupted JSON file")

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def _validate_string(self, s):
        if not isinstance(s, str) or not s.strip():
            raise ValueError("Invalid input")

    def add(self, title, director):
        self._validate_string(title)
        self._validate_string(director)
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"title": title, "director": director}
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
        self._validate_string(director)
        try:
            idx = int(id)
            if idx not in self.data["items"]:
                raise ValueError("ID not found")
        except (ValueError, TypeError):
            raise ValueError("Invalid ID")
        
        self.data["items"][idx]["director"] = director
        self._save()

    def remove(self, id):
        try:
            idx = int(id)
            if idx not in self.data["items"]:
                raise ValueError("ID not found")
            del self.data["items"][idx]
            self._save()
        except (ValueError, TypeError):
            raise ValueError("Invalid ID")
