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
                self.next_id = data["next_id"]
                self.items = {int(k): v for k, v in data["items"].items()}
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Damaged JSON file")
        else:
            self.next_id = 1
            self.items = {}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({"next_id": self.next_id, "items": self.items}, f)

    def add(self, text, author):
        if not text or not text.strip() or not author or not author.strip():
            raise ValueError("Empty text or author")
        new_id = self.next_id
        self.items[new_id] = {"text": text, "author": author}
        self.next_id += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.items.keys())
        return [{"id": i, "text": self.items[i]["text"], "author": self.items[i]["author"]} for i in sorted_ids]

    def set_author(self, id, author):
        if id not in self.items:
            raise ValueError("ID not found")
        if not author or not author.strip():
            raise ValueError("Empty author")
        self.items[id]["author"] = author
        self._save()

    def remove(self, id):
        if id not in self.items:
            raise ValueError("ID not found")
        del self.items[id]
        self._save()
