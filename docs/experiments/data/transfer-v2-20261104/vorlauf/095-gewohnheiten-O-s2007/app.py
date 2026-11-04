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
                        raise ValueError("Ungültiges Format")
                    self.items = data["items"]
                self._validate_items()
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Beschädigte Datei")
        else:
            self.items = []
        self._save()

    def _validate_items(self):
        for item in self.items:
            if not isinstance(item, dict) or "name" not in item or "active" not in item:
                raise ValueError("Ungültiges Format")
            if not isinstance(item["name"], str) or not item["name"].strip():
                raise ValueError("Ungültiger Name")
            if not isinstance(item["active"], bool):
                raise ValueError("Ungültiger Status")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({"items": self.items}, f)

    def add(self, name, active):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Ungültiger Name")
        if not isinstance(active, bool):
            raise ValueError("Ungültiger Status")
        self.items.append({"name": name, "active": active})
        self._save()

    def list(self):
        return [dict(item) for item in self.items]

    def set_active(self, index, active):
        if not isinstance(index, int) or index < 0 or index >= len(self.items):
            raise ValueError("Ungültiger Index")
        if not isinstance(active, bool):
            raise ValueError("Ungültiger Status")
        self.items[index]["active"] = active
        self._save()

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.items):
            raise ValueError("Ungültiger Index")
        self.items.pop(index)
        self._save()
