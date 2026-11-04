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
                    self.next_id = data["next_id"]
                    self.items = {int(k): v for k, v in data["items"].items()}
            except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                raise ValueError("Damaged or invalid JSON file")
        else:
            self.next_id = 1
            self.items = {}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({"next_id": self.next_id, "items": self.items}, f)

    def add(self, name, cuisine):
        if not name or not name.strip() or not cuisine or not cuisine.strip():
            raise ValueError("Name and cuisine must not be empty")
        new_id = self.next_id
        self.items[new_id] = {"name": name, "cuisine": cuisine}
        self.next_id += 1
        self._save()
        return new_id

    def list(self):
        result = []
        for k in sorted(self.items.keys()):
            item = self.items[k]
            result.append({"id": k, "name": item["name"], "cuisine": item["cuisine"]})
        return result

    def set_cuisine(self, id, cuisine):
        if id not in self.items:
            raise ValueError(f"ID {id} not found")
        if not cuisine or not cuisine.strip():
            raise ValueError("Cuisine must not be empty")
        self.items[id]["cuisine"] = cuisine
        self._save()

    def remove(self, id):
        if id not in self.items:
            raise ValueError(f"ID {id} not found")
        del self.items[id]
        self._save()
