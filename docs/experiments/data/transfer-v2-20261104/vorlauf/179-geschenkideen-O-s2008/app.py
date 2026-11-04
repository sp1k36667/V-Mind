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
                        raise ValueError("Invalid format")
                    self.data = loaded
            except (json.JSONDecodeError, ValueError):
                raise ValueError("File is corrupted")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def _validate_str(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid value")
        return value.strip()

    def add(self, idea, person):
        idea = self._validate_str(idea)
        person = self._validate_str(person)
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
        person = self._validate_str(person)
        self.data["items"][id]["person"] = person
        self._save()

    def remove(self, id):
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id]
        self._save()
