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
                self._validate_items()
            except (json.JSONDecodeError, ValueError, KeyError):
                raise ValueError("Damaged JSON file")
        else:
            self._items = []
            self._save()

    def _validate_items(self):
        for item in self._items:
            if not isinstance(item, dict) or "book" not in item or "minutes" not in item:
                raise ValueError("Invalid entry")
            if not isinstance(item["book"], str) or item["book"].strip() == "":
                raise ValueError("Invalid book")
            if not isinstance(item["minutes"], int) or isinstance(item["minutes"], bool) or item["minutes"] <= 0:
                raise ValueError("Invalid minutes")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({"items": self._items}, f)

    def add(self, book, minutes):
        if not isinstance(book, str) or book.strip() == "":
            raise ValueError("Invalid book")
        if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes <= 0:
            raise ValueError("Invalid minutes")
        
        self._items.append({"book": book, "minutes": minutes})
        self._save()

    def list(self):
        return [item.copy() for item in self._items]

    def total(self):
        return sum(item["minutes"] for item in self._items)

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self._items):
            raise ValueError("Invalid index")
        self._items.pop(index)
        self._save()
