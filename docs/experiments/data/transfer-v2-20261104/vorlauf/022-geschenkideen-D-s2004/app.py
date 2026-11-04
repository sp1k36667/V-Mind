import json
import os

class GiftIdeas:
    """Geschenkideen, dauerhaft gespeichert in der JSON-Datei `path`."""

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
                raise ValueError("Beschädigte Datei")

        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def _validate_string(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Ungültiger Wert")
        return value.strip()

    def add(self, idea, person):
        idea = self._validate_string(idea)
        person = self._validate_string(person)
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {
            "idea": idea,
            "person": person
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
                "idea": item["idea"],
                "person": item["person"]
            })
        return result

    def set_person(self, id, person):
        if not isinstance(id, int):
            id = int(id)
        if id not in self.data["items"]:
            raise ValueError("ID nicht gefunden")
        
        person = self._validate_string(person)
        self.data["items"][id]["person"] = person
        self._save()

    def remove(self, id):
        if not isinstance(id, int):
            id = int(id)
        if id not in self.data["items"]:
            raise ValueError("ID nicht gefunden")
        
        del self.data["items"][id]
        self._save()
