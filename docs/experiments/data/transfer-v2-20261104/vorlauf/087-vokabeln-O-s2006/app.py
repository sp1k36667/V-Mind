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
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("File is corrupted or invalid")
        else:
            self.data = {"next_id": 1, "items": {}}
            self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _validate_string(self, s):
        if not isinstance(s, str) or not s.strip():
            raise ValueError("String cannot be empty")
        return s.strip()

    def add(self, word, translation):
        """Legt einen Eintrag an und gibt seine neue ID (int) zurück."""
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
        """Liefert alle Einträge nach ID sortiert: [{\"id\": int, \"word\": str, \"translation\": str}, ...]."""
        result = []
        for key, val in self.data["items"].items():
            result.append({
                "id": int(key),
                "word": val["word"],
                "translation": val["translation"]
            })
        return sorted(result, key=lambda x: x["id"])

    def set_translation(self, id, translation):
        """Ändert \"translation\" des Eintrags mit der ID `id`."""
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        translation = self._validate_string(translation)
        
        key = str(id)
        if key not in self.data["items"]:
            raise ValueError(f"ID {id} not found")
        
        self.data["items"][key]["translation"] = translation
        self._save()

    def remove(self, id):
        """Löscht den Eintrag mit der ID `id`."""
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        
        key = str(id)
        if key not in self.data["items"]:
            raise ValueError(f"ID {id} not found")
        
        del self.data["items"][key]
        self._save()
