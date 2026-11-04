import json
import os

class Vocabulary:
    """Vokabelheft, dauerhaft gespeichert in der JSON-Datei `path`."""

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
                raise ValueError("Corrupted JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def _validate_string(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid input")
        return value.strip()

    def add(self, word, translation):
        word = self._validate_string(word)
        translation = self._validate_string(translation)
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {
            "word": word,
            "translation": translation
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_ids = sorted(self.data["items"].keys(), key=int)
        result = []
        for idx in sorted_ids:
            item = self.data["items"][idx]
            result.append({
                "id": int(idx),
                "word": item["word"],
                "translation": item["translation"]
            })
        return result

    def set_translation(self, id, translation):
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        translation = self._validate_string(translation)
        
        str_id = str(id)
        if str_id not in self.data["items"]:
            raise ValueError("ID not found")
        
        self.data["items"][str_id]["translation"] = translation
        self._save()

    def remove(self, id):
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        
        str_id = str(id)
        if str_id not in self.data["items"]:
            raise ValueError("ID not found")
        
        del self.data["items"][str_id]
        self._save()
