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
                        raise ValueError("Ungültiges Format")
                    self.data = loaded
                    # Sicherstellen, dass alle Keys in items Integers sind
                    new_items = {}
                    for k, v in loaded["items"].items():
                        new_items[int(k)] = v
                    self.data["items"] = new_items
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Beschädigte JSON-Datei")

        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def add(self, text, author):
        if not text or not text.strip() or not author or not author.strip():
            raise ValueError("Text und Autor dürfen nicht leer sein.")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {
            "text": str(text),
            "author": str(author)
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys())
        result = []
        for i in sorted_ids:
            item = self.data["items"][i]
            result.append({
                "id": i,
                "text": item["text"],
                "author": item["author"]
            })
        return result

    def set_author(self, id, author):
        if not author or not author.strip():
            raise ValueError("Autor darf nicht leer sein.")
        
        try:
            idx = int(id)
        except (ValueError, TypeError):
            raise ValueError("Ungültige ID")

        if idx not in self.data["items"]:
            raise ValueError("ID nicht gefunden")
        
        self.data["items"][idx]["author"] = str(author)
        self._save()

    def remove(self, id):
        try:
            idx = int(id)
        except (ValueError, TypeError):
            raise ValueError("Ungültige ID")

        if idx not in self.data["items"]:
            raise ValueError("ID nicht gefunden")
        
        del self.data["items"][idx]
        self._save()
