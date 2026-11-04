import json
import os

class Scoreboard:
    """Punktestand, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "items" not in data or not isinstance(data["items"], list):
                    raise ValueError("Invalid format")
                self.data = data
            except (json.JSONDecodeError, ValueError, KeyError):
                raise ValueError("Damaged JSON file")
        else:
            self.data = {"items": []}
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def _validate_points(self, points):
        if not isinstance(points, int) or isinstance(points, bool):
            raise ValueError("Points must be an integer")
        if points <= 0:
            raise ValueError("Points must be greater than 0")

    def add(self, player, points):
        if not isinstance(player, str) or not player.strip():
            raise ValueError("Invalid player name")
        self._validate_points(points)
        self.data["items"].append({"player": player, "points": points})
        self._save()

    def list(self):
        return self.data["items"]

    def total(self):
        return sum(item["points"] for item in self.data["items"])

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.data["items"]):
            raise ValueError("Invalid index")
        self.data["items"].pop(index)
        self._save()
