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
                raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def add(self, name, cuisine):
        if not name or not name.strip() or not cuisine or not cuisine.strip():
            raise ValueError("Name and cuisine must not be empty")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"name": str(name), "cuisine": str(cuisine)}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_items = []
        for key in sorted(self.data["items"].keys()):
            item = self.data["items"][key]
            sorted_items.append({
                "id": int(key),
                "name": item["name"],
                "cuisine": item["cuisine"]
            })
        return sorted_items

    def set_cuisine(self, id, cuisine):
        if not cuisine or not cuisine.strip():
            raise ValueError("Cuisine must not be empty")
        try:
            idx = int(id)
        except (ValueError, TypeError):
            raise ValueError("Invalid ID")
            
        if idx not in self.data["items"]:
            raise ValueError("ID not found")
            
        self.data["items"][idx]["cuisine"] = str(cuisine)
        self._save()

    def remove(self, id):
        try:
            idx = int(id)
        except (ValueError, TypeError):
            raise ValueError("Invalid ID")
            
        if idx not in self.data["items"]:
            raise ValueError("ID not found")
            
        del self.data["items"][idx]
        self._save()
