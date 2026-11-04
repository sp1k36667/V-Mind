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
                self._items = data["items"]
                for item in self._items:
                    self._validate_item(item)
            except (json.JSONDecodeError, ValueError, KeyError):
                raise ValueError("Corrupted file")
        else:
            self._items = []
        self._save()

    def _validate_item(self, item):
        if not isinstance(item, dict) or "player" not in item or "points" not in item:
            raise ValueError()
        if not isinstance(item["player"], str) or item["player"].strip() == "":
            raise ValueError()
        if not isinstance(item["points"], int) or isinstance(item["points"], bool) or item["points"] <= 0:
            raise ValueError()

    def _save(self):
        data = {"items": self._items}
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

    def add(self, player, points):
        if not isinstance(player, str) or player.strip() == "":
            raise ValueError()
        if not isinstance(points, int) or isinstance(points, bool) or points <= 0:
            raise ValueError()
        self._items.append({"player": player, "points": points})
        self._save()

    def list(self):
        return [dict(item) for item in self._items]

    def total(self):
        return sum(item["points"] for item in self._items)

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self._items):
            raise ValueError()
        self._items.pop(index)
        self._save()
