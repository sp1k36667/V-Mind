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
                self.data["next_id"] = content["next_id"]
                raw_items = content["items"]
                self.data["items"] = {}
                for k, v in raw_items.items():
                    self.data["items"][int(k)] = v
        except (json.JSONDecodeError, ValueError, TypeError, KeyError):
            raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add(self, word, translation):
        """Legt einen Eintrag an und gibt seine neue ID (int) zurück."""
        if not word or not word.strip() or not translation or not translation.strip():
            raise ValueError("Empty values")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {"word": word, "translation": translation}
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        """Liefert alle Einträge nach ID sortiert: [{\"id\": int, \"word\": str, \"translation\": str}, ...]."""
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
        """Ändert \"translation\" des Eintrags mit der ID `id`."""
        if not isinstance(id, int):
            try:
                id = int(id)
            except (ValueError, TypeError):
                raise ValueError("Invalid ID")
        
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        
        if not translation or not translation.strip():
            raise ValueError("Empty translation")
            
        self.data["items"][id]["translation"] = translation
        self._save()

    def remove(self, id):
        """Löscht den Eintrag mit der ID `id`."""
        if not isinstance(id, int):
            try:
                id = int(id)
            except (ValueError, TypeError):
                raise ValueError("Invalid ID")
                
        if id not in self.data["items"]:
            raise ValueError("ID not found")
            
        del self.data["items"][id]
        self._save()
