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
                    raise ValueError("Ungültiges Format")
                self.data = data
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Beschädigte Datei")
        else:
            self.data = {"items": []}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def _validate_minutes(self, minutes):
        if not isinstance(minutes, int) or isinstance(minutes, bool):
            raise ValueError("Ungültige Minuten")
        if minutes <= 0:
            raise ValueError("Minuten müssen größer als 0 sein")

    def add(self, exercise, minutes):
        if not isinstance(exercise, str) or not exercise.strip():
            raise ValueError("Ungültiger Übungsname")
        self._validate_minutes(minutes)
        self.data["items"].append({"exercise": exercise, "minutes": minutes})
        self._save()

    def list(self):
        return [item.copy() for item in self.data["items"]]

    def total(self):
        return sum(item["minutes"] for item in self.data["items"])

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.data["items"]):
            raise ValueError("Ungültiger Index")
        self.data["items"].pop(index)
        self._save()
