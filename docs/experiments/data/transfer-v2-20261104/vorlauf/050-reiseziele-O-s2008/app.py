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
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def add(self, place, country):
        if not place or not place.strip() or not country or not country.strip():
            raise ValueError("Empty input")
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {
            "place": place,
            "country": country
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        result = []
        for key, val in self.data["items"].items():
            result.append({
                "id": int(key),
                "place": val["place"],
                "country": val["country"]
            })
        return sorted(result, key=lambda x: x["id"])

    def set_country(self, id, country):
        if not country or not country.strip():
            raise ValueError("Empty input")
        if str(id) not in self.data["items"]:
            raise ValueError("ID not found")
        self.data["items"][str(id)]["country"] = country
        self._save()

    def remove(self, id):
        if str(id) not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(id)]
        self._save()
