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
                        raise ValueError
                    self.data = loaded
                    # Sicherstellen, dass alle Keys in items Integers sind
                    new_items = {}
                    for k, v in loaded["items"].items():
                        new_items[int(k)] = v
                    self.data["items"] = new_items
            except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                raise ValueError("Die Datei ist beschädigt oder ungültig.")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def add(self, idea, person):
        if not idea or not idea.strip() or not person or not person.strip():
            raise ValueError("Idea und Person dürfen nicht leer sein.")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"idea": idea, "person": person}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys())
        result = []
        for i in sorted_ids:
            item = self.data["items"][i]
            result.append({"id": i, "idea": item["idea"], "person": item["person"]})
        return result

    def set_person(self, id, person):
        if not isinstance(id, (int, str)) or int(id) not in self.data["items"]:
            raise ValueError("Ungültige ID.")
        if not person or not person.strip():
            raise ValueError("Person darf nicht leer sein.")
        
        self.data["items"][int(id)]["person"] = person
        self._save()

    def remove(self, id):
        if not isinstance(id, (int, str)) or int(id) not in self.data["items"]:
            raise ValueError("Ungültige ID.")
        
        del self.data["items"][int(id)]
        self._save()
