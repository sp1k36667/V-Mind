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
                    raise ValueError("Ungültiges Format")
                self.data = data
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Beschädigte oder ungültige Datei")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def _validate_string(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Ungültiger Text")
        return value.strip()

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
        for key, val in self.data["items"].items():
            result.append({"id": int(key), "text": val["text"], "author": val["author"]})
        return sorted(result, key=lambda x: x["id"])

    def set_author(self, id, author):
        id_str = str(id)
        if id_str not in self.data["items"]:
            raise ValueError("ID nicht gefunden")
        author = self._validate_string(author)
        self.data["items"][id_str]["author"] = author
        self._save()

    def remove(self, id):
        id_str = str(id)
        if id_str not in self.data["items"]:
            raise ValueError("ID nicht gefunden")
        del self.data["items"][id_str]
        self._save()
