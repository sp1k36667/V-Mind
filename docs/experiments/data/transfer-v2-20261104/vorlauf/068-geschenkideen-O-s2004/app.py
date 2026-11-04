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
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("File is corrupted or invalid")
        else:
            self.data = {"next_id": 1, "items": {}}
            self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def add(self, idea, person):
        if not idea or not idea.strip() or not person or not person.strip():
            raise ValueError("Empty input")
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {
            "idea": idea,
            "person": person
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        result = []
        for key, val in self.data["items"].items():
            result.append({
                "id": int(key),
                "idea": val["idea"],
                "person": val["person"]
            })
        return sorted(result, key=lambda x: x["id"])

    def set_person(self, id, person):
        if not person or not person.strip():
            raise ValueError("Empty input")
        
        key = str(id)
        if key not in self.data["items"]:
            raise ValueError("ID not found")
        
        self.data["items"][key]["person"] = person
        self._save()

    def remove(self, id):
        key = str(id)
        if key not in self.data["items"]:
            raise ValueError("ID not found")
        
        del self.data["items"][key]
        self._save()
