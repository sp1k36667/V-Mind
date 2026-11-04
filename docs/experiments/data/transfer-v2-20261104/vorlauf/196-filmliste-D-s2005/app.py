import json
import os

class FilmList:
    """Filmliste, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Validierung der Struktur
                    if not isinstance(loaded, dict) or "next_id" not in loaded or "items" not in loaded:
                        raise ValueError("Invalid format")
                    
                    # Validierung der items und Umwandlung der Keys in Integers
                    new_items = {}
                    for k, v in loaded["items"].items():
                        try:
                            int_k = int(k)
                            if int_k < loaded["next_id"]:
                                raise ValueError("ID reuse detected")
                            new_items[int_k] = v
                        except (ValueError, TypeError):
                            raise ValueError("Invalid ID in file")
                    
                    self.data["items"] = new_items
                    self.data["next_id"] = loaded["next_id"]
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Damaged or invalid JSON file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def add(self, title, director):
        if not title or not title.strip():
            raise ValueError("Title cannot be empty")
        if not director or not director.strip():
            raise ValueError("Director cannot be empty")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {
            "title": str(title),
            "director": str(director)
        }
        self.data["next_id"] += 1
        self._save()
        return new_id

    def list(self):
        sorted_items = []
        for fid in sorted(self.data["items"].keys()):
            item = self.data["items"][fid]
            sorted_items.append({
                "id": fid,
                "title": item["title"],
                "director": item["director"]
            })
        return sorted_items

    def set_director(self, id, director):
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        if id not in self.data["items"]:
            raise ValueError("ID not found")
        if not director or not director.strip():
            raise ValueError("Director cannot be empty")
            
        self.data["items"][id]["director"] = str(director)
        self._save()

    def remove(self, id):
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        if id not in self.data["items"]:
            raise ValueError("ID not found")
            
        del self.data["items"][id]
        self._save()
