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
                self.next_id = data["next_id"]
                self.items = {int(k): v for k, v in data["items"].items()}
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Damaged JSON file")
        else:
            self.next_id = 1
            self.items = {}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({"next_id": self.next_id, "items": self.items}, f)

    def add(self, place, country):
        if not place or not place.strip() or not country or not country.strip():
            raise ValueError("Empty values")
        new_id = self.next_id
        self.items[new_id] = {"place": str(place), "country": str(country)}
        self.next_id += 1
        self._save()
        return new_id

    def list(self):
        result = []
        for i in sorted(self.items.keys()):
            item = self.items[i]
            result.append({"id": i, "place": item["place"], "country": item["country"]})
        return result

    def set_country(self, id, country):
        if id not in self.items:
            raise ValueError("ID not found")
        if not country or not country.strip():
            raise ValueError("Empty value")
        self.items[id]["country"] = str(country)
        self._save()

    def remove(self, id):
        if id not in self.items:
            raise ValueError("ID not found")
        del self.items[id]
        self._save()
