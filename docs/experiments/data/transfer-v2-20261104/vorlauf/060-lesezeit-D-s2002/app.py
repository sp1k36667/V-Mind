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
                    raise ValueError("Ungültiges Format")
                self.items = data["items"]
            except (json.JSONDecodeError, ValueError, KeyError):
                raise ValueError("Beschädigte JSON-Datei")
        else:
            self.items = []
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({"items": self.items}, f, indent=2)

    def add(self, book, minutes):
        if not isinstance(book, str) or not book.strip():
            raise ValueError("Ungültiger Buchtitel")
        if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes <= 0:
            raise ValueError("Ungültige Minuten")
        self.items.append({"book": book, "minutes": minutes})
        self._save()

    def list(self):
        return list(self.items)

    def total(self):
        return sum(item["minutes"] for item in self.items)

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.items):
            raise ValueError("Ungültiger Index")
        self.items.pop(index)
        self._save()
