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
                    content = json.load(f)
                    if not isinstance(content, dict) or "next_id" not in content or "items" not in content:
                        raise ValueError("Invalid format")
                    self.data = content
                    # Ensure keys are integers
                    new_items = {}
                    for k, v in content["items"].items():
                        new_items[int(k)] = v
                    self.data["items"] = new_items
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Damaged JSON file")
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2)

    def _validate_string(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid input")

    def add(self, idea, person):
        self._validate_string(idea)
        self._validate_string(person)
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
        self._validate_string(person)
        try:
            int_id = int(id)
        except (ValueError, TypeError):
            raise ValueError("Invalid ID")
        if int_id not in self.data["items"]:
            raise ValueError("ID not found")
        self.data["items"][int_id]["person"] = person
        self._save()

    def remove(self, id):
        try:
            int_id = int(id)
        except (ValueError, TypeError):
            raise ValueError("Invalid ID")
        if int_id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][int_id]
        self._save()
