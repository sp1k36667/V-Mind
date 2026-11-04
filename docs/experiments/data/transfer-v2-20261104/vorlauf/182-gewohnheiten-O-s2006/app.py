import json
import os

class Habits:
    """Gewohnheiten, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if not isinstance(data, dict) or "items" not in data or not isinstance(data["items"], list):
                        raise ValueError("Invalid format")
                    self.items = data["items"]
            except (json.JSONDecodeError, ValueError, KeyError):
                raise ValueError("Corrupted file")
        else:
            self.items = []
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({"items": self.items}, f, indent=4)

    def add(self, name, active):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Invalid name")
        if not isinstance(active, bool):
            raise ValueError("Active must be boolean")
        self.items.append({"name": name.strip(), "active": active})
        self._save()

    def list(self):
        return [item.copy() for item in self.items]

    def set_active(self, index, active):
        if not isinstance(index, int) or index < 0 or index >= len(self.items):
            raise ValueError("Invalid index")
        if not isinstance(active, bool):
            raise ValueError("Active must be boolean")
        self.items[index]["active"] = active
        self._save()

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.items):
            raise ValueError("Invalid index")
        self.items.pop(index)
        self._save()
