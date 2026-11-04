import json
import os

class Budget:
    """Haushaltsbuch, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "items" not in data or not isinstance(data["items"], list):
                    raise ValueError("Invalid format")
                self.items = data["items"]
            except (json.JSONDecodeError, ValueError):
                raise ValueError("File is corrupted")
        else:
            self.items = []
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({"items": self.items}, f)

    def add(self, category, cents):
        if not category or not category.strip():
            raise ValueError("Category must not be empty")
        if not isinstance(cents, int) or cents <= 0 or isinstance(cents, bool):
            raise ValueError("Cents must be a positive integer")
        self.items.append({"category": str(category), "cents": cents})
        self._save()

    def list(self):
        return [item.copy() for item in self.items]

    def total(self):
        return sum(item["cents"] for item in self.items)

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.items):
            raise ValueError("Invalid index")
        self.items.pop(index)
        self._save()
