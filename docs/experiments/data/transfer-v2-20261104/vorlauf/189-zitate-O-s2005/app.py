import json
import os

class Quotes:
    """Zitatsammlung, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def _validate_string(self, s):
        if not s or not s.strip():
            raise ValueError("Empty string")
        return s.strip()

    def add(self, text, author):
        text = self._validate_string(text)
        author = self._validate_string(author)
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {"text": text, "author": author}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        result = []
        sorted_keys = sorted(self.data["items"].keys(), key=int)
        for k in sorted_keys:
            item = self.data["items"][k]
            result.append({
                "id": int(k),
                "text": item["text"],
                "author": item["author"]
            })
        return result

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
