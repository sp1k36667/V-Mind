import json
import os

class Importer:
    """Zählt Zahlungen, dauerhaft gespeichert in der JSON-Datei `path`."""

    def __init__(self, path):
        self.path = path
        self.data = {"ids": [], "total_cents": 0}
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        self._save()

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def ingest(self, event_id, cents):
        """Verarbeitet eine Zahlung; True, wenn sie gezählt wurde, sonst False."""
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("Invalid event_id")
        if not isinstance(cents, int) or cents <= 0:
            raise ValueError("Invalid cents")

        if event_id in self.data["ids"]:
            return False

        self.data["ids"].append(event_id)
        self.data["total_cents"] += cents
        self._save()
        return True

    def total(self):
        """Liefert die Summe aller gezählten Zahlungen in Cent (int)."""
        return self.data["total_cents"]
