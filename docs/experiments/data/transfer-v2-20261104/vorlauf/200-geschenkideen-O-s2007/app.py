import json
import os

class GiftIdeas:
    """Geschenkideen, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if not isinstance(loaded, dict) or "next_id" not in loaded or "items" not in loaded:
                        raise ValueError("Invalid format")
                    self.data = loaded
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f)

    def _validate_strings(self, *args):
        for arg in args:
            if not isinstance(arg, str) or not arg.strip():
                raise ValueError("Invalid input")

    def add(self, idea, person):
        self._validate_strings(idea, person)
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"idea": idea, "person": person}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        result = []
        for key in sorted(self.data["items"].keys(), key=int):
            item = self.data["items"][key]
            result.append({
                "id": int(key),
                "idea": item["idea"],
                "person": item["person"]
            })
        return result

    def set_person(self, id, person):
        self._validate_strings(person)
        if not isinstance(id, int) or str(id) not in self.data["items"]:
            raise ValueError("ID not found")
        self.data["items"][str(id)]["person"] = person
        self._save()

    def remove(self, id):
        if not isinstance(id, int) or str(id) not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(id)]
        self._save()
