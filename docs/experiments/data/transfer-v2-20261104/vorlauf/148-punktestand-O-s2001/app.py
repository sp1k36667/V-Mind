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
                        if not isinstance(item, dict) or "player" not in item or "points" not in item:
                            raise ValueError("Invalid item")
                        if not isinstance(item["player"], str) or item["player"].strip() == "":
                            raise ValueError("Invalid player")
                        if not isinstance(item["points"], int) or item["points"] <= 0 or isinstance(item["points"], bool):
                            raise ValueError("Invalid points")
                self.data = data
            except (json.JSONDecodeError, ValueError, KeyError, TypeError):
                raise ValueError("Corrupted JSON file")
        else:
            self.data = {"items": []}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def add(self, player, points):
        if not isinstance(player, str) or player.strip() == "":
            raise ValueError("Invalid player")
        if not isinstance(points, int) or points <= 0 or isinstance(points, bool):
            raise ValueError("Invalid points")
        
        self.data["items"].append({"player": player, "points": points})
        self._save()

    def list(self):
        return list(self.data["items"])

    def total(self):
        return sum(item["points"] for item in self.data["items"])

    def remove(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.data["items"]):
            raise ValueError("Invalid index")
        self.data["items"].pop(index)
        self._save()
