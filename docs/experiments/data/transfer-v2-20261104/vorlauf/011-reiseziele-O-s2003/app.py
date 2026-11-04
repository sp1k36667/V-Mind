import json
import os

class Destinations:
    """Reiseziele, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                    raise ValueError("Invalid format")
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def _validate_string(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid value")

    def add(self, place, country):
        self._validate_string(place)
        self._validate_string(country)
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {
            "place": place,
            "country": country
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys(), key=int)
        result = []
        for s_id in sorted_ids:
            item = self.data["items"][s_id]
            result.append({
                "id": int(s_id),
                "place": item["place"],
                "country": item["country"]
            })
        return result

    def set_country(self, id, country):
        if not isinstance(id, int):
            raise ValueError("ID must be int")
        self._validate_string(country)
        
        s_id = str(id)
        if s_id not in self.data["items"]:
            raise ValueError("ID not found")
        
        self.data["items"][s_id]["country"] = country
        self._save()

    def remove(self, id):
        if not isinstance(id, int):
            raise ValueError("ID must be int")
        
        s_id = str(id)
        if s_id not in self.data["items"]:
            raise ValueError("ID not found")
        
        del self.data["items"][s_id]
        self._save()
