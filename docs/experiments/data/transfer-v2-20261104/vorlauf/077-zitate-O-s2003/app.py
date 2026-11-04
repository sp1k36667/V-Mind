import json
import os

class Quotes:
    """Zitatsammlung, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                if not isinstance(self.data, dict) or "next_id" not in self.data or "items" not in self.data:
                    raise ValueError("Invalid format")
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted JSON file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def _validate_string(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid input")
        return value.strip()

    def add(self, text, author):
        text = self._validate_string(text)
        author = self._validate_string(author)
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {
            "text": text,
            "author": author
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        result = []
        for key, val in self.data["items"].items():
            result.append({
                "id": int(key),
                "text": val["text"],
                "author": val["author"]
            })
        return sorted(result, key=lambda x: x["id"])

    def set_author(self, id, author):
        author = self._validate_string(author)
        str_id = str(id)
        if str_id not in self.data["items"]:
            raise ValueError("ID not found")
        self.data["items"][str_id]["author"] = author
        self._save()

    def remove(self, id):
        str_id = str(id)
        if str_id not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str_id]
        self._save()
