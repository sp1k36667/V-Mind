import json
import os

class Destinations:
    """Reiseziele, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                        raise ValueError("Invalid format")
                    self.data = data
                    # Ensure keys are integers
                    self.data["items"] = {int(k): v for k, v in data["items"].items()}
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Corrupted or invalid JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}
            self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def add(self, place, country):
        if not place or not place.strip() or not country or not country.strip():
            raise ValueError("Place and country must not be empty")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {
            "place": str(place),
            "country": str(country)
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        result = []
        for idx in sorted(self.data["items"].keys()):
            item = self.data["items"][idx]
            result.append({
                "id": idx,
                "place": item["place"],
                "country": item["country"]
            })
        return result

    def set_country(self, id, country):
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        if not country or not country.strip():
            raise ValueError("Country cannot be empty")
        
        self.data["items"][id]["country"] = str(country)
        self._save()

    def remove(self, id):
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        
        del self.data["items"][id]
        self._save()
