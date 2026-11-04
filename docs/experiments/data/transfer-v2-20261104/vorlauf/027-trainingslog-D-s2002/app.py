import json
import os

class TrainingLog:
    """Trainingsprotokoll, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"items": []}
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if not isinstance(loaded, dict) or "items" not in loaded:
                        raise ValueError("Invalid format")
                    self.data = loaded
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def add(self, exercise, minutes):
        if not isinstance(exercise, str) or not exercise.strip():
            raise ValueError("Invalid exercise")
        if type(minutes) is not int or minutes <= 0:
            raise ValueError("Invalid minutes")
        
        self.data["items"].append({"exercise": exercise, "minutes": minutes})
        self._save()

    def list(self):
        return self.data["items"]

    def total(self):
        return sum(item["minutes"] for item in self.data["items"])

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.data["items"]):
            raise ValueError("Invalid index")
        self.data["items"].pop(index)
        self._save()
