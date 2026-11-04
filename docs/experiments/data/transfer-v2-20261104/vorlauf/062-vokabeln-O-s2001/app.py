import json
import os

class Vocabulary:
    """Vokabelheft, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return {"next_id": 1, "items": {}}
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
                    raise ValueError("Invalid format")
                return data
        except (json.JSONDecodeError, ValueError):
            raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def add(self, word, translation):
        if not word or not word.strip() or not translation or not translation.strip():
            raise ValueError("Empty values not allowed")
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {
            "word": str(word),
            "translation": str(translation)
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        items = []
        for key, val in self.data["items"].items():
            items.append({
                "id": int(key),
                "word": val["word"],
                "translation": val["translation"]
            })
        return sorted(items, key=lambda x: x["id"])

    def set_translation(self, id, translation):
        if not translation or not translation.strip():
            raise ValueError("Empty translation not allowed")
        
        key = str(id)
        if key not in self.data["items"]:
            raise ValueError("ID not found")
        
        self.data["items"][key]["translation"] = str(translation)
        self._save()

    def remove(self, id):
        key = str(id)
        if key not in self.data["items"]:
            raise ValueError("ID not found")
        
        del self.data["items"][key]
        self._save()
