import json
import os

class RecipeIdeas:
    """Rezeptideen, dauerhaft gespeichert in der JSON-Datei `path`."""

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
                raise ValueError("Damaged JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def _validate_string(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid value")
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
        for item_id in sorted(self.data["items"].keys()):
            item = self.data["items"][item_id]
            result.append({
                "id": item_id,
                "name": item["name"],
                "cuisine": item["cuisine"]
            })
        return result

    def set_cuisine(self, id, cuisine):
        if not isinstance(id, int) or id not in self.data["items"]:
            raise ValueError("ID not found")
        cuisine = self._validate_string(cuisine)
        self.data["items"][id]["cuisine"] = cuisine
        self._save()

    def remove(self, id):
        if not isinstance(id, int) or id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id]
        self._save()
