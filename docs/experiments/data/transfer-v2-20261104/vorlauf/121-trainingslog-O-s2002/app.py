import json
import os

class TrainingLog:
    """Trainingsprotokoll, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"items": []}
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    content = f.read()
                    if not content.strip():
                        raise ValueError("Empty file")
                    loaded = json.loads(content)
                    if not isinstance(loaded, dict) or "items" not in loaded or not isinstance(loaded["items"], list):
                        raise ValueError("Invalid format")
                    self.data = loaded
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted or invalid JSON file")

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def add(self, exercise, minutes):
        if not isinstance(exercise, str) or not exercise.strip():
            raise ValueError("Invalid exercise")
        if not isinstance(minutes, int) or minutes <= 0 or isinstance(minutes, bool):
            raise ValueError("Minutes must be a positive integer")
        
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
