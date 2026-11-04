class Package:
    """Status eines Pakets aus eintreffenden Ereignissen."""

    STATUS_ORDER = ["created", "in_transit", "out_for_delivery", "delivered"]

    def __init__(self):
        self._current_status = "created"

    def apply(self, event):
        """Verarbeitet ein Ereignis."""
        if not isinstance(event, str):
            raise ValueError("Event must be a string")
        
        if event not in self.STATUS_ORDER:
            raise ValueError("Unknown status")
            
        current_index = self.STATUS_ORDER.index(self._current_status)
        new_index = self.STATUS_ORDER.index(event)
        
        if new_index > current_index:
            self._current_status = event

    def status(self):
        """Liefert den aktuellen Status (str)."""
        return self._current_status
