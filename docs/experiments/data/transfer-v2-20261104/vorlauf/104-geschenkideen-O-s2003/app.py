import json
import os

class GiftIdeas:
    """Geschenkideen, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _validate_str(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid value")
        return value.strip()

    def add(self, idea, person):
        idea = self._validate_str(idea)
        person = self._validate_str(person)
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"idea": idea, "person": person}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted([int(k) for k in self.data["items"].keys()])
        result = []
        for i in sorted_ids:
            item = self.data["items"][str(i)]
            result.append({"id": i, "idea": item["idea"], "person": item["person"]})
        return result

    def set_person(self, id, person):
        id_str = str(id)
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        person = self._validate_str(person)
        self.data["items"][id_str]["person"] = person
        self._save()

    def remove(self, id):
        id_str = str(id)
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id_str]
        self._save()
