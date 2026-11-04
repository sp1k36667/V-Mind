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
                raise ValueError("File is corrupted or invalid")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def _validate_str(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Value must be a non-empty string")
        return value.strip()

    def add(self, text, author):
        text = self._validate_str(text)
        author = self._validate_str(author)
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"text": text, "author": author}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted([int(k) for k in self.data["items"].keys()])
        result = []
        for i in sorted_ids:
            item = self.data["items"][str(i)]
            result.append({"id": i, "text": item["text"], "author": item["author"]})
        return result

    def set_author(self, id, author):
        if not isinstance(id, int) or str(id) not in self.data["items"]:
            raise ValueError("ID not found")
        author = self._validate_str(author)
        self.data["items"][str(id)]["author"] = author
        self._save()

    def remove(self, id):
        if not isinstance(id, int) or str(id) not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][str(id)]
        self._save()
