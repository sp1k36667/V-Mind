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
                # Convert keys to integers immediately
                self.data["items"] = {int(k): v for k, v in data["items"].items()}
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Corrupted or invalid JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}
            self.save()

    def save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def _validate_string(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("String must not be empty")
        return value.strip()

    def add(self, name, cuisine):
        name = self._validate_string(name)
        cuisine = self._validate_string(cuisine)
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {
            "name": name,
            "cuisine": cuisine
        }
        self.data["next_id"] += 1
        self.save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys())
        result = []
        for rid in sorted_ids:
            item = self.data["items"][rid]
            result.append({
                "id": rid,
                "name": item["name"],
                "cuisine": item["cuisine"]
            })
        return result

    def set_cuisine(self, id, cuisine):
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        
        cuisine = self._validate_string(cuisine)
        self.data["items"][id]["cuisine"] = cuisine
        self.save()

    def remove(self, id):
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        
        del self.data["items"][id]
        self.save()
