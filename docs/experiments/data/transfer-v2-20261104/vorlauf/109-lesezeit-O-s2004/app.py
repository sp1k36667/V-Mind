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
                    self._items = data["items"]
            except (json.JSONDecodeError, ValueError, KeyError):
                raise ValueError("Corrupted file")
        else:
            self._items = []
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({"items": self._items}, f)

    def add(self, book, minutes):
        if not isinstance(book, str) or not book.strip():
            raise ValueError("Invalid book")
        if not isinstance(minutes, int) or minutes <= 0 or isinstance(minutes, bool):
            raise ValueError("Invalid minutes")
        
        self._items.append({"book": book, "minutes": minutes})
        self._save()

    def list(self):
        return list(self._items)

    def total(self):
        return sum(item["minutes"] for item in self._items)

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self._items):
            raise ValueError("Invalid index")
        self._items.pop(index)
        self._save()
