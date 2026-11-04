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
                    content = f.read()
                    if not content:
                        raise ValueError("Datei ist leer")
                    loaded = json.loads(content)
                    if not isinstance(loaded, dict) or "next_id" not in loaded or "items" not in loaded:
                        raise ValueError("Ungültiges Format")
                    self.data = loaded
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Beschädigte JSON-Datei")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def _validate_string(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Ungültiger String")
        return value.strip()

    def add(self, name, cuisine):
        name = self._validate_string(name)
        cuisine = self._validate_string(cuisine)
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"name": name, "cuisine": cuisine}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        result = []
        for id_key, val in self.data["items"].items():
            result.append({"id": int(id_key), "name": val["name"], "cuisine": val["cuisine"]})
        return sorted(result, key=lambda x: x["id"])

    def set_cuisine(self, id, cuisine):
        if str(id) not in self.data["items"]:
            raise ValueError("ID existiert nicht")
        cuisine = self._validate_string(cuisine)
        self.data["items"][str(id)]["cuisine"] = cuisine
        self._save()

    def remove(self, id):
        if str(id) not in self.data["items"]:
            raise ValueError("ID existiert nicht")
        del self.data["items"][str(id)]
        self._save()
