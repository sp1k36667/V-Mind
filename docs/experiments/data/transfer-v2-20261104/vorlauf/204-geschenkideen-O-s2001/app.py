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
                    loaded_data = json.load(f)
                    if not isinstance(loaded_data, dict) or "next_id" not in loaded_data or "items" not in loaded_data:
                        raise ValueError("Invalid format")
                    self.data = loaded_data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def _validate_string(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid input")
        return value.strip()

    def add(self, idea, person):
        idea = self._validate_string(idea)
        person = self._validate_string(person)
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"idea": idea, "person": person}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        result = []
        for iid in sorted(self.data["items"].keys()):
            item = self.data["items"][iid]
            result.append({"id": iid, "idea": item["idea"], "person": item["person"]})
        return result

    def set_person(self, id, person):
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        person = self._validate_string(person)
        self.data["items"][id]["person"] = person
        self._save()

    def remove(self, id):
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id]
        self._save()
