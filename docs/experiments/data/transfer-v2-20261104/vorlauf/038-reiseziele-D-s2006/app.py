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
                        raise ValueError("Ungültiges Format")
                    self.data = loaded
                    # Sicherstellen, dass alle Keys in items Integers sind
                    new_items = {}
                    for k, v in loaded["items"].items():
                        new_items[int(k)] = v
                    self.data["items"] = new_items
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Beschädigte oder ungültige JSON-Datei")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def add(self, place, country):
        if not place or not place.strip() or not country or not country.strip():
            raise ValueError("Platz und Land dürfen nicht leer sein.")
        
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
        if not country or not country.strip():
            raise ValueError("Land darf nicht leer sein.")
        
        try:
            target_id = int(id)
        except (ValueError, TypeError):
            raise ValueError("Ungültige ID")
            
        if target_id not in self.data["items"]:
            raise ValueError("ID nicht gefunden")
            
        self.data["items"][target_id]["country"] = str(country)
        self._save()

    def remove(self, id):
        try:
            target_id = int(id)
        except (ValueError, TypeError):
            raise ValueError("Ungültige ID")
            
        if target_id not in self.data["items"]:
            raise ValueError("ID nicht gefunden")
            
        del self.data["items"][target_id]
        self._save()
