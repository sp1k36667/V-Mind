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
                    self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged file")
        else:
            self.data = {"items": []}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_liters(self, liters):
        if type(liters) is not int or liters <= 0:
            raise ValueError("Invalid liters")

    def add(self, room, liters):
        if not isinstance(room, str) or not room.strip():
            raise ValueError("Invalid room")
        self._validate_liters(liters)
        self.data["items"].append({"room": room, "liters": liters})
        self._save()

    def list(self):
        return self.data["items"]

    def total(self):
        return sum(item["liters"] for item in self.data["items"])

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.data["items"]):
            raise ValueError("Invalid index")
        self.data["items"].pop(index)
        self._save()
