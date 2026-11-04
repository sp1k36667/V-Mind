import json
import os

class FilmList:
    """Filmliste, dauerhaft gespeichert in der JSON-Datei `path`."""

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
                raise ValueError("Damaged or invalid JSON file")
        else:
            self.data = {"next_id": 1, "items": {}}
        self._save()

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _validate_string(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid value")
        return value.strip()

    def add(self, title, director):
        """Legt einen Eintrag an und gibt seine neue ID (int) zurück."""
        title = self._validate_string(title)
        director = self._validate_string(director)
        
        new_id = self.data["next_id"]
        self.data["items"][str(new_id)] = {
            "title": title,
            "director": director
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        """Liefert alle Einträge nach ID sortiert: [{\"id\": int, \"title\": str, \"director\": str}, ...]."""
        result = []
        for key, val in self.data["items"].items():
            result.append({
                "id": int(key),
                "title": val["title"],
                "director": val["director"]
            })
        return sorted(result, key=lambda x: x["id"])

    def set_director(self, id, director):
        """Ändert \"director\" des Eintrags mit der ID `id`."""
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        if str(id) not in self.data["items"]:
            raise ValueError("ID not found")
        
        director = self._validate_string(director)
        self.data["items"][str(id)]["director"] = director
        self._save()

    def remove(self, id):
        """Löscht den Eintrag mit der ID `id`."""
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        if str(id) not in self.data["items"]:
            raise ValueError("ID not found")
        
        del self.data["items"][str(id)]
        self._save()
