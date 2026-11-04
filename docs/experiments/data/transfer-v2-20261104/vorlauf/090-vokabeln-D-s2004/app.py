import json
import os

class Vocabulary:
    """Vokabelheft, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                if not isinstance(content, dict) or "next_id" not in content or "items" not in content:
                    raise ValueError("Invalid format")
                self.data = content
                # Ensure keys are integers
                self.data["items"] = {int(k): v for k, v in content["items"].items()}
        except (json.JSONDecodeError, ValueError, TypeError):
            raise ValueError("Corrupted or invalid JSON file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def add(self, word, translation):
        if not word or not word.strip():
            raise ValueError("Word cannot be empty")
        if not translation or not translation.strip():
            raise ValueError("Translation cannot be empty")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {
            "word": word,
            "translation": translation
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
                "word": item["word"],
                "translation": item["translation"]
            })
        return result

    def set_translation(self, id, translation):
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        if not translation or not translation.strip():
            raise ValueError("Translation cannot be empty")
        
        self.data["items"][id]["translation"] = translation
        self._save()

    def remove(self, id):
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        
        del self.data["items"][id]
        self._save()
