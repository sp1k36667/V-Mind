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
            json.dump(self.data, f, indent=2)

    def _validate_string(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid input")
        return value.strip()

    def add(self, idea, person):
        idea = self._validate_string(idea)
        person = self._validate_string(person)
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"idea": idea, "person": person}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        result = []
        sorted_ids = sorted(self.data["items"].keys(), key=int)
        for sid in sorted_ids:
            item = self.data["items"][sid]
            result.append({
                "id": int(sid),
                "idea": item["idea"],
                "person": item["person"]
            })
        return result

    def set_person(self, id, person):
        sid = str(id)
        if sid not in self.data["items"]:
            raise ValueError("ID not found")
        person = self._validate_string(person)
        self.data["items"][sid]["person"] = person
        self._save()

    def remove(self, id):
        sid = str(id)
        if sid not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][sid]
        self._save()
