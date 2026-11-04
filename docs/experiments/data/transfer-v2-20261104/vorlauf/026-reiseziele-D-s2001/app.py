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
                raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def add(self, place, country):
        if not place or not place.strip() or not country or not country.strip():
            raise ValueError("Empty values")
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"place": place, "country": country}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys())
        result = []
        for i in sorted_ids:
            item = self.data["items"][i]
            result.append({"id": i, "place": item["place"], "country": item["country"]})
        return result

    def set_country(self, id, country):
        if not isinstance(id, int) or id not in self.data["items"]:
            raise ValueError("Invalid ID")
        if not country or not country.strip():
            raise ValueError("Empty value")
        self.data["items"][id]["country"] = country
        self._save()

    def remove(self, id):
        if not isinstance(id, int) or id not in self.data["items"]:
            raise ValueError("Invalid ID")
        del self.data["items"][id]
        self._save()
