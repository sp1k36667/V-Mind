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
                self.data = data
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"items": []}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False)

    def _validate_cents(self, cents):
        if not isinstance(cents, int) or isinstance(cents, bool):
            raise ValueError("Cents must be an integer")
        if cents <= 0:
            raise ValueError("Cents must be greater than 0")

    def add(self, category, cents):
        if not isinstance(category, str) or not category.strip():
            raise ValueError("Invalid category")
        self._validate_cents(cents)
        self.data["items"].append({"category": category, "cents": cents})
        self._save()

    def list(self):
        return [item.copy() for item in self.data["items"]]

    def total(self):
        return sum(item["cents"] for item in self.data["items"])

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.data["items"]):
            raise ValueError("Invalid index")
        self.data["items"].pop(index)
        self._save()
