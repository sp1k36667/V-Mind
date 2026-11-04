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
                    # Ensure keys are integers
                    self.data["items"] = {int(k): v for k, v in data["items"].items()}
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Corrupted or invalid JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}
            self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def add(self, text, author):
        if not text or not text.strip() or not author or not author.strip():
            raise ValueError("Text and author must not be empty")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"text": text, "author": author}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys())
        result = []
        for id_key in sorted_ids:
            item = self.data["items"][id_key]
            result.append({
                "id": id_key,
                "text": item["text"],
                "author": item["author"]
            })
        return result

    def set_author(self, id, author):
        if not isinstance(id, int):
            try:
                id = int(id)
            except (ValueError, TypeError):
                raise ValueError("ID must be an integer")
        
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        
        if not author or not author.strip():
            raise ValueError("Author must not be empty")
            
        self.data["items"][id]["author"] = author
        self._save()

    def remove(self, id):
        if not isinstance(id, int):
            try:
                id = int(id)
            except (ValueError, TypeError):
                raise ValueError("ID must be an integer")
        
        if id not in self.data["items"]:
            raise ValueError("ID not found")
            
        del self.data["items"][id]
        self._save()
