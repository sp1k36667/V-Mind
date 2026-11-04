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
            except (json.JSONDecodeError, ValueError, KeyError):
                raise ValueError("Corrupted JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _validate_strings(self, *args):
        for arg in args:
            if not isinstance(arg, str) or not arg.strip():
                raise ValueError("Invalid input")

    def add(self, text, author):
        self._validate_strings(text, author)
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
        self._validate_strings(author)
        key = str(id)
        if key not in self.data["items"]:
            raise ValueError("ID not found")
        self.data["items"][key]["author"] = author
        self._save()

    def remove(self, id):
        key = str(id)
        if key not in self.data["items"]:
            raise ValueError("ID not found")
        del self.data["items"][key]
        self._save()
