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
                if "items" not in data or not isinstance(data["items"], list):
                    raise ValueError("Invalid format")
                self.items = data["items"]
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")
        else:
            self.items = []
            self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump({"items": self.items}, f)

    def add(self, plant, interval_days):
        if not isinstance(plant, str) or not plant.strip():
            raise ValueError("Invalid plant name")
        if not isinstance(interval_days, int) or isinstance(interval_days, bool) or interval_days <= 0:
            raise ValueError("Invalid interval_days")
        
        self.items.append({"plant": plant, "interval_days": interval_days})
        self._save()

    def list(self):
        return list(self.items)

    def total(self):
        return sum(item["interval_days"] for item in self.items)

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.items):
            raise ValueError("Invalid index")
        self.items.pop(index)
        self._save()
