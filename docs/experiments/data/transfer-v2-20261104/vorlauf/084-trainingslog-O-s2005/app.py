import json
import os

class TrainingLog:
    """Trainingsprotokoll, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "items" not in data or not isinstance(data["items"], list):
                    raise ValueError("Invalid format")
                self.items = data["items"]
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file")
        else:
            self.items = []
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({"items": self.items}, f)

    def add(self, exercise, minutes):
        if not isinstance(exercise, str) or not exercise.strip():
            raise ValueError("Invalid exercise")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("minutes must be a positive integer")
        self.items.append({"exercise": exercise, "minutes": minutes})
        self._save()

    def list(self):
        return list(self.items)

    def total(self):
        return sum(item["minutes"] for item in self.items)

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.items):
            raise ValueError("Invalid index")
        self.items.pop(index)
        self._save()
