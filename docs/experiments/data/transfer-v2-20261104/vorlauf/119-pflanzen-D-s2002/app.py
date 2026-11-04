import json
import os

class PlantCare:
    """Gießplan, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"items": []}
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if not isinstance(loaded, dict) or "items" not in loaded or not isinstance(loaded["items"], list):
                        raise ValueError("Invalid format")
                    self.data = loaded
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def add(self, plant, interval_days):
        if not isinstance(plant, str) or not plant.strip():
            raise ValueError("Invalid plant name")
        if not isinstance(interval_days, int) or isinstance(interval_days, bool) or interval_days <= 0:
            raise ValueError("Invalid interval")
        
        self.data["items"].append({
            "plant": plant,
            "interval_days": interval_days
        })
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
