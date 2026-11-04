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
            except (json.JSONDecodeError, ValueError, KeyError):
                raise ValueError("Damaged or invalid JSON file")
        else:
            self.items = []
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({"items": self.items}, f)

    def _validate_cents(self, cents):
        if not isinstance(cents, int) or isinstance(cents, bool) or cents <= 0:
            raise ValueError("Invalid cents")

    def add(self, category, cents):
        if not isinstance(category, str) or category.strip() == "":
            raise ValueError("Invalid category")
        self._validate_cents(cents)
        self.items.append({"category": category, "cents": cents})
        self._save()

    def list(self):
        return list(self.items)

    def total(self):
        return sum(item["cents"] for item in self.items)

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.items):
            raise ValueError("Invalid index")
        self.items.pop(index)
        self._save()
