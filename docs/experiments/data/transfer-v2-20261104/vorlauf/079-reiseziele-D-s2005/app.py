import json
import os

class Destinations:
    """Reiseziele, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if not isinstance(loaded, dict) or "next_id" not in loaded or "items" not in loaded:
                        raise ValueError("Invalid format")
                    
                    # Convert keys to integers
                    new_items = {}
                    for k, v in loaded["items"].items():
                        new_items[int(k)] = v
                    
                    self.data = {"next_id": loaded["next_id"], "items": new_items}
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Corrupted or invalid JSON file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def add(self, place, country):
        if not place or not place.strip() or not country or not country.strip():
            raise ValueError("Empty values not allowed")
        
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
        for id_key in sorted(self.data["items"].keys()):
            item = self.data["items"][id_key]
            result.append({
                "id": id_key,
                "place": item["place"],
                "country": item["country"]
            })
        return result

    def set_country(self, id, country):
        if not country or not country.strip():
            raise ValueError("Empty value not allowed")
        
        try:
            idx = int(id)
        except (ValueError, TypeError):
            raise ValueError("Invalid ID")
            
        if idx not in self.data["items"]:
            raise ValueError("ID not found")
            
        self.data["items"][idx]["country"] = str(country)
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
