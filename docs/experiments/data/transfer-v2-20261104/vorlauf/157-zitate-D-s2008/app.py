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
                    raw_data = json.load(f)
                    if not isinstance(raw_data, dict) or "next_id" not in raw_data or "items" not in raw_data:
                        raise ValueError("Invalid format")
                    self.data["next_id"] = raw_data["next_id"]
                    self.data["items"] = {int(k): v for k, v in raw_data["items"].items()}
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Corrupted JSON file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)

    def add(self, text, author):
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        if not author or not author.strip():
            raise ValueError("Author cannot be empty")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"text": text, "author": author}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys())
        result = []
        for i in sorted_ids:
            item = self.data["items"][i]
            result.append({"id": i, "text": item["text"], "author": item["author"]})
        return result

    def set_author(self, id, author):
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        if not author or not author.strip():
            raise ValueError("Author cannot be empty")
        
        self.data["items"][id]["author"] = author
        self._save()

    def remove(self, id):
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        
        del self.data["items"][id]
        self._save()
