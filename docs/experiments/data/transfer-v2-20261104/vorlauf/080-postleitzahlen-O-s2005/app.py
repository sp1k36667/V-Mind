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
                    loaded = json.load(f)
                    if not isinstance(loaded, dict) or "items" not in loaded:
                        raise ValueError("Invalid format")
                    self.data = loaded
            except (json.JSONDecodeError, ValueError):
                raise ValueError("Corrupted JSON file")

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def _validate_code(self, code):
        if not isinstance(code, str) or not (len(code) == 5 and code.isdigit()):
            raise ValueError("Invalid postcode format")

    def add(self, code, city):
        self._validate_code(code)
        if not isinstance(city, str) or not city.strip():
            raise ValueError("Invalid city name")
        self.data["items"][code] = city.strip()
        self._save()

    def city(self, code):
        self._validate_code(code)
        if code not in self.data["items"]:
            raise ValueError("Postcode not found")
        return self.data["items"][code]

    def list(self):
        result = []
        for code in sorted(self.data["items"].keys()):
            result.append({"code": code, "city": self.data["items"][code]})
        return result

    def remove(self, code):
        self._validate_code(code)
        if code not in self.data["items"]:
            raise ValueError("Postcode not found")
        del self.data["items"][code]
        self._save()
