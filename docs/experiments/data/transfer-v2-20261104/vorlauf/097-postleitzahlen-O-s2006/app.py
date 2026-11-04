import json
import os

class Postcodes:
    """Postleitzahlenverzeichnis, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"items": {}}
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    if not isinstance(content, dict) or "items" not in content:
                        raise ValueError("Ungültiges Format")
                    self.data = content
                    if not isinstance(self.data["items"], dict):
                        raise ValueError("Ungültiges Format")
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Beschädigte Datei")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2)

    def _validate_code(self, code):
        if not isinstance(code, str) or not (code.isdigit() and len(code) == 5):
            raise ValueError("Ungültige Postleitzahl")

    def _validate_city(self, city):
        if not isinstance(city, str) or not city.strip():
            raise ValueError("Ungültiger Ort")

    def add(self, code, city):
        self._validate_code(code)
        self._validate_city(city)
        self.data["items"][code] = city
        self._save()

    def city(self, code):
        self._validate_code(code)
        if code not in self.data["items"]:
            raise ValueError("Postleitzahl nicht gefunden")
        return self.data["items"][code]

    def list(self):
        result = []
        for code in sorted(self.data["items"].keys()):
            result.append({"code": code, "city": self.data["items"][code]})
        return result

    def remove(self, code):
        self._validate_code(code)
        if code not in self.data["items"]:
            raise ValueError("Postleitzahl nicht gefunden")
        del self.data["items"][code]
        self._save()
