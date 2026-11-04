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
                    # Ensure keys are integers
                    new_items = {}
                    for k, v in loaded["items"].items():
                        new_items[int(k)] = v
                    self.data["items"] = new_items
            except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                raise ValueError("Corrupted JSON file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def add(self, word, translation):
        if not word or not word.strip():
            raise ValueError("Word cannot be empty")
        if not translation or not translation.strip():
            raise ValueError("Translation cannot be empty")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {
            "word": str(word),
            "translation": str(translation)
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
        try:
            idx = int(id)
        except (ValueError, TypeError):
            raise ValueError("Invalid ID")
            
        if idx not in self.data["items"]:
            raise ValueError("ID not found")
        if not translation or not translation.strip():
            raise ValueError("Translation cannot be empty")
            
        self.data["items"][idx]["translation"] = str(translation)
        self._save()

    def remove(self, id):
        try:
            idx = int(id)
        except (ValueError, TypeError):
            raise ValueError("Invalid ID")
            
        if idx not in self.data["items"]:
            raise ValueError("ID not found")
            
        del self.data["items"][idx]
        self._save()
