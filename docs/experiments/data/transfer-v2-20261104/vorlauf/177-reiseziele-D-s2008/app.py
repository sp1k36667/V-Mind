import json
import os

class Destinations:
    """Reiseziele, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            self._save()
            return
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                self.data = content
                # Ensure keys are integers and next_id is int
                self.data["next_id"] = int(self.data["next_id"])
                processed_items = {}
                for k, v in self.data["items"].items():
                    processed_items[int(k)] = v
                self.data["items"] = processed_items
        except (json.JSONDecodeError, ValueError, TypeError, KeyError):
            raise ValueError("Die Datei ist beschädigt oder ungültig.")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def add(self, place, country):
        if not place or not place.strip() or not country or not country.strip():
            raise ValueError("Platz und Land dürfen nicht leer sein.")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {
            "place": place,
            "country": country
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_items = []
        for entry_id in sorted(self.data["items"].keys()):
            item = self.data["items"][entry_id]
            sorted_items.append({
                "id": entry_id,
                "place": item["place"],
                "country": item["country"]
            })
        return sorted_items

    def set_country(self, id, country):
        if not isinstance(id, int) or id not in self.data["items"]:
            raise ValueError(f"ID {id} existiert nicht.")
        if not country or not country.strip():
            raise ValueError("Land darf nicht leer sein.")
        
        self.data["items"][id]["country"] = country
        self._save()

    def remove(self, id):
        if not isinstance(id, int) or id not in self.data["items"]:
            raise ValueError(f"ID {id} existiert nicht.")
        
        del self.data["items"][id]
        self._save()
