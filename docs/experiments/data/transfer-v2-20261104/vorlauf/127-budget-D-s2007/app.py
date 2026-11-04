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
            except (json.JSONDecodeError, ValueError, KeyError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"items": []}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def _validate_cents(self, cents):
        if type(cents) is not int or cents <= 0:
            raise ValueError("Invalid cents")

    def add(self, category, cents):
        if not isinstance(category, str) or not category.strip():
            raise ValueError("Invalid category")
        self._validate_cents(cents)
        self.data["items"].append({"category": category, "cents": cents})
        self._save()

    def list(self):
        return self.data["items"]

    def total(self):
        return sum(item["cents"] for item in self.data["items"])

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.data["items"]):
            raise ValueError("Invalid index")
        self.data["items"].pop(index)
        self._save()
