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
                    self.next_id = data["next_id"]
                    self.items = {int(k): v for k, v in data["items"].items()}
                if not isinstance(self.next_id, int):
                    raise ValueError("Invalid next_id type")
            except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                raise ValueError("Damaged JSON file")
        else:
            self.next_id = 1
            self.items = {}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({"next_id": self.next_id, "items": self.items}, f)

    def add(self, idea, person):
        if not idea or not idea.strip() or not person or not person.strip():
            raise ValueError("Idea and person cannot be empty")
        new_id = self.next_id
        self.items[new_id] = {"idea": idea, "person": person}
        self.next_id += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.items.keys())
        result = []
        for i in sorted_ids:
            item = self.items[i]
            result.append({"id": i, "idea": item["idea"], "person": item["person"]})
        return result

    def set_person(self, id, person):
        if id not in self.items:
            raise ValueError("ID not found")
        if not person or not person.strip():
            raise ValueError("Person cannot be empty")
        self.items[id]["person"] = person
        self._save()

    def remove(self, id):
        if id not in self.items:
            raise ValueError("ID not found")
        del self.items[id]
        self._save()
