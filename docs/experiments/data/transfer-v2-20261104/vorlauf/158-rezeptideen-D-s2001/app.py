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
                    # Ensure keys are integers
                    new_items = {}
                    for k, v in loaded["items"].items():
                        new_items[int(k)] = v
                    self.data["items"] = new_items
            except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)

    def add(self, name, cuisine):
        if not name or not name.strip():
            raise ValueError("Name cannot be empty")
        if not cuisine or not cuisine.strip():
            raise ValueError("Cuisine cannot be empty")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"name": str(name), "cuisine": str(cuisine)}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys())
        result = []
        for i in sorted_ids:
            item = self.data["items"][i]
            result.append({"id": i, "name": item["name"], "cuisine": item["cuisine"]})
        return result

    def set_cuisine(self, id, cuisine):
        if not isinstance(id, int):
            try:
                id = int(id)
            except (ValueError, TypeError):
                raise ValueError("Invalid ID")
        
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        if not cuisine or not cuisine.strip():
            raise ValueError("Cuisine cannot be empty")
            
        self.data["items"][id]["cuisine"] = str(cuisine)
        self._save()

    def remove(self, id):
        if not isinstance(id, int):
            try:
                id = int(id)
            except (ValueError, TypeError):
                raise ValueError("Invalid ID")
                
        if id not in self.data["items"]:
            raise ValueError("ID not found")
            
        del self.data["items"][id]
        self._save()
