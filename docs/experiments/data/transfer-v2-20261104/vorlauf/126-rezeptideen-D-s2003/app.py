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
                self.next_id = data.get("next_id", 1)
                self.items = {}
                for k, v in data.get("items", {}).items():
                    self.items[int(k)] = v
            except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                raise ValueError("Damages JSON file.")
        else:
            self.next_id = 1
            self.items = {}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({"next_id": self.next_id, "items": self.items}, f)

    def add(self, name, cuisine):
        if not name or not name.strip() or not cuisine or not cuisine.strip():
            raise ValueError("Empty name or cuisine.")
        new_id = self.next_id
        self.items[new_id] = {"name": str(name), "cuisine": str(cuisine)}
        self.next_id += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.items.keys())
        return [{"id": i, "name": self.items[i]["name"], "cuisine": self.items[i]["cuisine"]} for i in sorted_ids]

    def set_cuisine(self, id, cuisine):
        if id not in self.items:
            raise ValueError("ID not found.")
        if not cuisine or not cuisine.strip():
            raise ValueError("Empty cuisine.")
        self.items[id]["cuisine"] = str(cuisine)
        self._save()

    def remove(self, id):
        if id not in self.items:
            raise ValueError("ID not found.")
        del self.items[id]
        self._save()
