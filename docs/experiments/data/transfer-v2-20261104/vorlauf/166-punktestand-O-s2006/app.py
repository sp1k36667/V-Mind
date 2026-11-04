import json
import os

class Scoreboard:
    """Punktestand, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if not isinstance(data, dict) or "items" not in data or not isinstance(data["items"], list):
                        raise ValueError("Invalid format")
                    for item in data["items"]:
                        self._validate_item(item)
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file")
        else:
            self._save_data({"items": []})

    def _validate_item(self, item):
        if not isinstance(item, dict) or "player" not in item or "points" not in item:
            raise ValueError()
        if not isinstance(item["player"], str) or not item["player"].strip():
            raise ValueError()
        p = item["points"]
        if not isinstance(p, int) or isinstance(p, bool) or p <= 0:
            raise ValueError()

    def _save_data(self, data):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

    def _load_data(self):
        with open(self.path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data["items"]:
                self._validate_item(item)
            return data["items"]

    def add(self, player, points):
        if not isinstance(player, str) or not player.strip():
            raise ValueError()
        if not isinstance(points, int) or isinstance(points, bool) or points <= 0:
            raise ValueError()
        
        items = self._load_data()
        items.append({"player": player, "points": points})
        self._save_data({"items": items})

    def list(self):
        return self._load_data()

    def total(self):
        items = self._load_data()
        return sum(item["points"] for item in items)

    def remove(self, index):
        items = self._load_data()
        if not isinstance(index, int) or index < 0 or index >= len(items):
            raise ValueError()
        items.pop(index)
        self._save_data({"items": items})
