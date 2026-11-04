import json
import os

class TrainingLog:
    """Trainingsprotokoll, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                    if not isinstance(data, dict) or "items" not in data or not isinstance(data["items"], list):
                        raise ValueError("Invalid format")
                    self._items = data["items"]
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted JSON file")
        else:
            self._items = []
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump({"items": self._items}, f)

    def add(self, exercise, minutes):
        if not isinstance(exercise, str) or not exercise.strip():
            raise ValueError("Invalid exercise")
        if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes <= 0:
            raise ValueError("Invalid minutes")
        
        self._items.append({"exercise": exercise, "minutes": minutes})
        self._save()

    def list(self):
        return list(self._items)

    def total(self):
        return sum(item["minutes"] for item in self._items)

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self._items):
            raise ValueError("Invalid index")
        self._items.pop(index)
        self._save()
