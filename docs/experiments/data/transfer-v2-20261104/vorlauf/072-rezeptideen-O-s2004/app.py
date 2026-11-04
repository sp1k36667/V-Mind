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
                raise ValueError("Corrupted JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}
            self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)

    def _validate_string(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid string value")
        return value.strip()

    def add(self, name, cuisine):
        name = self._validate_string(name)
        cuisine = self._validate_string(cuisine)
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {
            "name": name,
            "cuisine": cuisine
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        result = []
        for key, val in self.data["items"].items():
            result.append({
                "id": int(key),
                "name": val["name"],
                "cuisine": val["cuisine"]
            })
        return sorted(result, key=lambda x: x["id"])

    def set_cuisine(self, id, cuisine):
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        str_id = str(id)
        if str_id not in self.data["items"]:
            raise ValueError("ID not found")
        
        cuisine = self._validate_string(cuisine)
        self.data["items"][str_id]["cuisine"] = cuisine
        self._save()

    def remove(self, id):
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        str_id = str(id)
        if str_id not in self.data["items"]:
            raise ValueError("ID not found")
        
        del self.data["items"][str_id]
        self._save()
