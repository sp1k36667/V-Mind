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
                raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def _validate_strings(self, *args):
        for arg in args:
            if not isinstance(arg, str) or not arg.strip():
                raise ValueError("Invalid value")

    def add(self, idea, person):
        self._validate_strings(idea, person)
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"idea": idea, "person": person}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        result = []
        for id in sorted(self.data["items"].keys()):
            item = self.data["items"][id]
            result.append({"id": id, "idea": item["idea"], "person": item["person"]})
        return result

    def set_person(self, id, person):
        self._validate_strings(person)
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        self.data["items"][id]["person"] = person
        self._save()

    def remove(self, id):
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id]
        self._save()
