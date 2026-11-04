import json
import os

class PlantCare:
    """Gießplan, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"items": []}
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    loaded = json.load(f)
                    if not isinstance(loaded, dict) or "items" not in loaded or not isinstance(loaded["items"], list):
                        raise ValueError("Ungültiges Format")
                    self.data = loaded
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Beschädigte Datei")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, plant, interval_days):
        if not isinstance(plant, str) or not plant.strip():
            raise ValueError("Ungültiger Pflanzenname")
        if not isinstance(interval_days, int) or interval_days <= 0 or isinstance(interval_days, bool):
            raise ValueError("Ungültiges Intervall")
        
        self.data["items"].append({"plant": plant, "interval_days": interval_days})
        self._save()

    def list(self):
        return self.data["items"]

    def total(self):
        return sum(item["interval_days"] for item in self.data["items"])

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.data["items"]):
            raise ValueError("Ungültiger Index")
        self.data["items"].pop(index)
        self._save()
