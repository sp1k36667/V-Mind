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
                    # Ensure keys are integers
                    self.data = {"next_id": data["next_id"], "items": {int(k): v for k, v in data["items"].items()}}
                if not isinstance(self.data["next_id"], int):
                    raise ValueError("next_id must be int")
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Damaged JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def add(self, idea, person):
        if not idea or not idea.strip() or not person or not person.strip():
            raise ValueError("Empty values")
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
        if not isinstance(id, int) or id not in self.data["items"]:
            raise ValueError("Invalid ID")
        if not person or not person.strip():
            raise ValueError("Empty value")
        self.data["items"][id]["person"] = person
        self._save()

    def remove(self, id):
        if not isinstance(id, int) or id not in self.data["items"]:
            raise ValueError("Invalid ID")
        del self.data["items"][id]
        self._save()
