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
                raise ValueError("Damaged JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def _validate_string(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid value")
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
        result = []
        for key, val in self.data["items"].items():
            result.append({
                "id": int(key),
                "word": val["word"],
                "translation": val["translation"]
            })
        return sorted(result, key=lambda x: x["id"])

    def set_translation(self, id, translation):
        id_str = str(id)
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        
        translation = self._validate_string(translation)
        self.data["items"][id_str]["translation"] = translation
        self._save()

    def remove(self, id):
        id_str = str(id)
        if id_str not in self.data["items"]:
            raise ValueError("ID not found")
        
        del self.data["items"][id_str]
        self._save()
