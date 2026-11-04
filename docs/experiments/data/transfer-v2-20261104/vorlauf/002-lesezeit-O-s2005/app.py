import json
import os

class ReadingLog:
    """Lesezeiten, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                    if not isinstance(data, dict) or "items" not in data or not isinstance(data["items"], list):
                        raise ValueError("Invalid format")
                    self._data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted or invalid JSON file")
        else:
            self._data = {"items": []}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self._data, f)

    def _validate_minutes(self, minutes):
        if not isinstance(minutes, int) or isinstance(minutes, bool):
            raise ValueError("Minutes must be an integer")
        if minutes <= 0:
            raise ValueError("Minutes must be greater than 0")

    def add(self, book, minutes):
        if not isinstance(book, str) or not book.strip():
            raise ValueError("Book must be a non-empty string")
        self._validate_minutes(minutes)
        self._data["items"].append({"book": book, "minutes": minutes})
        self._save()

    def list(self):
        return [item.copy() for item in self._data["items"]]

    def total(self):
        return sum(item["minutes"] for item in self._data["items"])

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self._data["items"]):
            raise ValueError("Invalid index")
        self._data["items"].pop(index)
        self._save()
