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
                    self.next_id = data["next_id"]
                    self.items = {int(k): v for k, v in data["items"].items()}
                # Validate all items have required keys
                for k, v in self.items.items():
                    if not isinstance(v, dict) or "word" not in v or "translation" not in v:
                        raise ValueError("Invalid item content")
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Corrupted or invalid JSON file")
        else:
            self.next_id = 1
            self.items = {}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({"next_id": self.next_id, "items": self.items}, f, ensure_ascii=False, indent=2)

    def add(self, word, translation):
        if not word or not word.strip() or not translation or not translation.strip():
            raise ValueError("Word and translation must not be empty")
        
        new_id = self.next_id
        self.items[new_id] = {"word": word, "translation": translation}
        self.next_id += 1
        self._save()
        return new_id

    def list(self):
        sorted_items = sorted(self.items.items())
        return [{"id": k, "word": v["word"], "translation": v["translation"]} for k, v in sorted_items]

    def set_translation(self, id, translation):
        if id not in self.items:
            raise ValueError("ID not found")
        if not translation or not translation.strip():
            raise ValueError("Translation must not be empty")
        
        self.items[id]["translation"] = translation
        self._save()

    def remove(self, id):
        if id not in self.items:
            raise ValueError("ID not found")
        del self.items[id]
        self._save()
