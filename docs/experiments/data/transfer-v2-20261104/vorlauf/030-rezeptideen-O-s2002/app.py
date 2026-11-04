import json
import os

class RecipeIdeas:
    """Rezeptideen, dauerhaft gespeichert in der JSON-Datei `path`."""

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
                raise ValueError("File is corrupted or invalid")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def _validate_strings(self, *args):
        for arg in args:
            if not isinstance(arg, str) or not arg.strip():
                raise ValueError("Invalid input")

    def add(self, name, cuisine):
        self._validate_strings(name, cuisine)
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"name": name, "cuisine": cuisine}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        result = []
        for id_key, val in self.data["items"].items():
            if not isinstance(id_key, int):
                raise ValueError("Internal error")
            result.append({"id": id_key, "name": val["name"], "cuisine": val["cuisine"]})
        return sorted(result, key=lambda x: x["id"])

    def set_cuisine(self, id, cuisine):
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        self._validate_strings(cuisine)
        self.data["items"][id]["cuisine"] = cuisine
        self._save()

    def remove(self, id):
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id]
        self._save()
