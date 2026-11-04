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
                    # Validierung der Struktur
                    if not isinstance(loaded, dict) or "next_id" not in loaded or "items" not in loaded:
                        raise ValueError("Invalid format")
                    
                    # Keys in items zu ints konvertieren
                    new_items = {}
                    for k, v in loaded["items"].items():
                        try:
                            new_items[int(k)] = v
                        except (ValueError, TypeError):
                            raise ValueError("Invalid ID in file")
                    
                    self.data["next_id"] = loaded["next_id"]
                    self.data["items"] = new_items
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted JSON file")
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def add(self, place, country):
        if not place or not place.strip() or not country or not country.strip():
            raise ValueError("Empty values not allowed")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {
            "place": place,
            "country": country
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys())
        result = []
        for i in sorted_ids:
            item = self.data["items"][i]
            result.append({
                "id": i,
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
            raise ValueError("Empty country not allowed")
        
        self.data["items"][id]["country"] = country
        self._save()

    def remove(self, id):
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        
        del self.data["items"][id]
        self._save()
