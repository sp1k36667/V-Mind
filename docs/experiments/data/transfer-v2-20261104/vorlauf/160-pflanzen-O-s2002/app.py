import json
import os

class PlantCare:
    """Gießplan, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self._data = {"items": []}
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    content = f.read()
                    if not content.strip():
                        raise ValueError("Empty file")
                    loaded = json.load(f)
                    if not isinstance(loaded, dict) or "items" not in loaded or not isinstance(loaded["items"], list):
                        raise ValueError("Invalid structure")
                    self._data = loaded
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self._data, f)

    def add(self, plant, interval_days):
        if not isinstance(plant, str) or not plant.strip():
            raise ValueError("Invalid plant name")
        if not isinstance(interval_days, int) or interval_days <= 0:
            if isinstance(interval_days, bool):
                raise ValueError("Boolean not allowed")
            raise ValueError("interval_days must be a positive integer")
        
        self._data["items"].append({"plant": plant, "interval_days": interval_days})
        self._save()

    def list(self):
        return self._data["items"]

    def total(self):
        return sum(item["interval_days"] for item in self._data["items"])

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self._data["items"]):
            raise ValueError("Invalid index")
        self._data["items"].pop(index)
        self._save()
