import json
import os

class WaterMeter:
    """Wasserverbrauch, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "items" not in data or not isinstance(data["items"], list):
                    raise ValueError("Invalid format")
                self.items = data["items"]
            except (json.JSONDecodeError, ValueError, KeyError):
                raise ValueError("Corrupted file")
        else:
            self.items = []
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump({"items": self.items}, f)

    def add(self, room, liters):
        if not isinstance(room, str) or not room.strip():
            raise ValueError("Invalid room")
        if not isinstance(liters, int) or liters <= 0 or isinstance(liters, bool):
            raise ValueError("Invalid liters")
        self.items.append({"room": room, "liters": liters})
        self._save()

    def list(self):
        return list(self.items)

    def total(self):
        return sum(item["liters"] for item in self.items)

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.items):
            raise ValueError("Invalid index")
        self.items.pop(index)
        self._save()
