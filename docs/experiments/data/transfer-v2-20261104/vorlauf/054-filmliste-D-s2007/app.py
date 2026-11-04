import json
import os

class FilmList:
    """Filmliste, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"next_id": 1, "items": {}}
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    if not isinstance(content, dict) or "next_id" not in content or "items" not in content:
                        raise ValueError("Invalid format")
                    self.data = content
                    # Ensure keys are integers
                    new_items = {}
                    for k, v in content["items"].items():
                        new_items[int(k)] = v
                    self.data["items"] = new_items
            except (json.JSONDecodeError, ValueError, TypeError):
                raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def add(self, title, director):
        if not title or not title.strip() or not director or not director.strip():
            raise ValueError("Title and director must not be empty")
        
        new_id = self.data["next_id"]
        self.data["items"][new_id] = {
            "title": title,
            "director": director
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
                "title": item["title"],
                "director": item["director"]
            })
        return result

    def set_director(self, id, director):
        if id not in self.data["items"]:
            raise ValueError(f"ID {id} not found")
        if not director or not director.strip():
            raise ValueError("Director must not be empty")
        
        self.data["items"][id]["director"] = director
        self._save()

    def remove(self, id):
        if id not in self.data["items"]:
            raise ValueError(f"ID {id} not found")
        
        del self.data["items"][id]
        self._save()
