import json
import os

class GiftIdeas:
    """Geschenkideen, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                self.data = {"next_id": data["next_id"], "items": {}}
                for k, v in data["items"].items():
                    self.data["items"][int(k)] = v
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                raise ValueError("Die Datei ist beschädigt oder ungültig.")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, idea, person):
        if not idea or not idea.strip() or not person or not person.strip():
            raise ValueError("Texte dürfen nicht leer sein.")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"idea": idea, "person": person}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_items = []
        for idx in sorted(self.data["items"].keys()):
            item = self.data["items"][idx]
            sorted_items.append({"id": idx, "idea": item["idea"], "person": item["person"]})
        return sorted_items

    def set_person(self, id, person):
        if not person or not person.strip():
            raise ValueError("Personenname darf nicht leer sein.")
        if id not in self.data["items"]:
            raise ValueError("ID nicht gefunden.")
        
        self.data["items"][id]["person"] = person
        self._save()

    def remove(self, id):
        if id not in self.data["items"]:
            raise ValueError("ID nicht gefunden.")
        del self.data["items"][id]
        self._save()
