import json
import os

class Quotes:
    """Zitatsammlung, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if not isinstance(loaded, dict) or "next_id" not in loaded or "items" not in loaded:
                        raise ValueError("Invalid format")
                    self.data = loaded
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

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
        for key, value in self.data["items"].items():
            result.append({
                "id": int(key),
                "text": value["text"],
                "author": value["author"]
            })
        return sorted(result, key=lambda x: x["id"])

    def set_author(self, id, author):
        id_str = str(id)
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        author = self._validate_string(author)
        self.data["items"][id_str]["author"] = author
        self._save()

    def remove(self, id):
        id_str = str(id)
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][id_str]
        self._save()
