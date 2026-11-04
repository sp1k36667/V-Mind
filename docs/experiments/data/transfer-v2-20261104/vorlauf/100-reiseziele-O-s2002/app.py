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
                    self.data = loaded
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2)

    def _validate_string(self, s):
        if not isinstance(s, str) or not s.strip():
            raise ValueError("Invalid string")
        return s.strip()

    def add(self, place, country):
        place = self._validate_string(place)
        country = self._validate_string(country)
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"place": place, "country": country}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        result = []
        for key, val in self.data["items"].items():
            result.append({"id": int(key), "place": val["place"], "country": val["country"]})
        return sorted(result, key=lambda x: x["id"])

    def set_country(self, id, country):
        id_str = str(id)
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        country = self._validate_string(country)
        self.data["items"][id_str]["country"] = country
        self._save()

    def remove(self, id):
        id_str = str(id)
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id_str]
        self._save()
