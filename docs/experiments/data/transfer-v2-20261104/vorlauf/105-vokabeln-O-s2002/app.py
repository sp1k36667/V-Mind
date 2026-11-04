import json
import os

class Vocabulary:
    """Vokabelheft, dauerhaft gespeichert in der JSON-Datei `path`."""

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
                raise ValueError("File is corrupted")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

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
        sorted_ids = sorted(self.data["items"].keys(), key=int)
        result = []
        for sid in sorted_ids:
            item = self.data["items"][sid]
            result.append({
                "id": int(sid),
                "word": item["word"],
                "translation": item["translation"]
            })
        return result

    def set_translation(self, id, translation):
        sid = str(id)
        if sid not in self.data["items"]:
            raise ValueError("ID not found")
        
        translation = self._validate_string(translation)
        self.data["items"][sid]["translation"] = translation
        self._save()

    def remove(self, id):
        sid = str(id)
        if sid not in self.data["items"]:
            raise ValueError("ID not found")
        
        del self.data["items"][sid]
        self._save()
