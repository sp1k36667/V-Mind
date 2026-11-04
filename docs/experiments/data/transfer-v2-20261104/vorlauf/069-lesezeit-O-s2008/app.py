import json
import os

class ReadingLog:
    """Lesezeiten, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "items" not in data or not isinstance(data["items"], list):
                    raise ValueError("Invalid format")
                self._data = data
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Corrupted file")
        else:
            self._data = {"items": []}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f)

    def add(self, book, minutes):
        if not isinstance(book, str) or not book.strip():
            raise ValueError("Invalid book")
        if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes <= 0:
            raise ValueError("Invalid minutes")
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
