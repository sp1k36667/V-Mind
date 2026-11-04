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
            except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                raise ValueError("Corrupted file")
        else:
            self.next_id = 1
            self.items = {}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({"next_id": self.next_id, "items": self.items}, f)

    def add(self, idea, person):
        if not idea or not idea.strip() or not person or not person.strip():
            raise ValueError("Empty values not allowed")
        new_id = self.next_id
        self.items[new_id] = {"idea": idea, "person": person}
        self.next_id += 1
        self._save()
        return new_id

    def list(self):
        sorted_keys = sorted(self.items.keys())
        return [{"id": k, "idea": self.items[k]["idea"], "person": self.items[k]["person"]} for k in sorted_keys]

    def set_person(self, id, person):
        if not isinstance(id, int) or id not in self.items:
            raise ValueError("Invalid ID")
        if not person or not person.strip():
            raise ValueError("Empty value not allowed")
        self.items[id]["person"] = person
        self._save()

    def remove(self, id):
        if not isinstance(id, int) or id not in self.items:
            raise ValueError("Invalid ID")
        del self.items[id]
        self._save()
