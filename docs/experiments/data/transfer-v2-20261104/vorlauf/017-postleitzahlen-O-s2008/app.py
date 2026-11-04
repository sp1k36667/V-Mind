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
                        raise ValueError("Invalid format")
                    self.data = content
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Damaged JSON file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False)

    def _validate_code(self, code):
        if not isinstance(code, str) or not (code.isdigit() and len(code) == 5):
            raise ValueError("Invalid postcode format")

    def add(self, code, city):
        self._validate_code(code)
        if not city or not city.strip():
            raise ValueError("City cannot be empty")
        self.data["items"][code] = city.strip()
        self._save()

    def city(self, code):
        self._validate_code(code)
        if code not in self.data["items"]:
            raise ValueError("Postcode not found")
        return self.data["items"][code]

    def list(self):
        sorted_items = []
        for code in sorted(self.data["items"].keys()):
            sorted_items.append({"code": code, "city": self.data["items"][code]})
        return sorted_items

    def remove(self, code):
        self._validate_code(code)
        if code not in self.data["items"]:
            raise ValueError("Postcode not found")
        del self.data["items"][code]
        self._save()
