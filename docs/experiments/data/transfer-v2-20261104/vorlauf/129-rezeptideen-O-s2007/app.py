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
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _validate_str(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid value")
        return value.strip()

    def add(self, name, cuisine):
        name = self._validate_str(name)
        cuisine = self._validate_str(cuisine)
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"name": name, "cuisine": cuisine}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        result = []
        for id_str, content in self.data["items"].items():
            try:
                id_int = int(id_str)
                result.append({"id": id_int, "name": content["name"], "cuisine": content["cuisine"]})
            except ValueError:
                raise ValueError("Invalid ID in storage")
        return sorted(result, key=lambda x: x["id"])

    def set_cuisine(self, id, cuisine):
        cuisine = self._validate_str(cuisine)
        try:
            id_int = int(id)
            if id_int not in self.data["items"]:
                raise ValueError("ID not found")
            self.data["items"][str(id_int)]["cuisine"] = cuisine
            self._save()
        except (ValueError, TypeError):
            raise ValueError("Invalid ID")

    def remove(self, id):
        try:
            id_int = int(id)
            if id_int not in self.data["items"]:
                raise ValueError("ID not found")
            del self.data["items"][str(id_int)]
            self._save()
        except (ValueError, TypeError):
            raise ValueError("Invalid ID")
