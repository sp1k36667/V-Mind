import json
import os

class Habits:
    """Gewohnheiten, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"items": []}
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if not isinstance(loaded, dict) or "items" not in loaded or not isinstance(loaded["items"], list):
                        raise ValueError("Invalid format")
                    self.data = loaded
                    for item in self.data["items"]:
                        if not isinstance(item, dict) or "name" not in item or "active" not in item:
                            raise ValueError("Invalid entry")
                        if not isinstance(item["name"], str) or not item["name"].strip():
                            raise ValueError("Invalid name")
                        if not isinstance(item["active"], bool):
                            raise ValueError("Invalid active status")
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def add(self, name, active):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Invalid name")
        if not isinstance(active, bool):
            raise ValueError("active must be boolean")
        self.data["items"].append({"name": name, "active": active})
        self._save()

    def list(self):
        return [item.copy() for item in self.data["items"]]

    def set_active(self, index, active):
        if not isinstance(index, int) or index < 0 or index >= len(self.data["items"]):
            raise ValueError("Invalid index")
        if not isinstance(active, bool):
            raise ValueError("active must be boolean")
        self.data["items"][index]["active"] = active
        self._save()

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.data["items"]):
            raise ValueError("Invalid index")
        self.data["items"].pop(index)
        self._save()
