import json
import os

class PlantCare:
    """Gießplan, dauerhaft gespeichert in der JSON-Datei `path`."""

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
                raise ValueError("Corrupted or invalid JSON file")
        else:
            self.data = {"items": []}
            self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_interval(self, value):
        if type(value) is not int or value <= 0:
            raise ValueError("Interval must be a positive integer")

    def add(self, plant, interval_days):
        if not isinstance(plant, str) or not plant.strip():
            raise ValueError("Plant must be a non-empty string")
        self._validate_interval(interval_days)
        self.data["items"].append({"plant": plant, "interval_days": interval_days})
        self._save()

    def list(self):
        return self.data["items"]

    def total(self):
        return sum(item["interval_days"] for item in self.data["items"])

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.data["items"]):
            raise ValueError("Invalid index")
        self.data["items"].pop(index)
        self._save()
