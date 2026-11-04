class Waitlist:
    """Kurs mit begrenzten Plätzen und Warteliste."""

    def __init__(self, capacity):
        if not isinstance(capacity, int) or capacity < 1:
            raise ValueError("Capacity must be a positive integer.")
        self.capacity = capacity
        self.bookings = []
        self.next_id = 1

    def book(self, name):
        """Legt eine Buchung an und gibt ihre neue ID (int) zurück."""
        if not name or name.isspace():
            raise ValueError("Name cannot be empty.")
        
        booking_id = self.next_id
        self.bookings.append({
            "id": booking_id,
            "name": name,
            "active": True,
            "confirmed": False
        })
        self.next_id += 1
        return booking_id

    def cancel(self, booking_id):
        """Storniert die Buchung mit der ID `booking_id`."""
        booking = next((b for b in self.bookings if b["id"] == booking_id), None)
        if booking is None or not booking["active"]:
            raise ValueError("Invalid or already cancelled booking ID.")
        
        booking["active"] = False
        self._update_status()

    def _update_status(self):
        """Interne Methode zur Aktualisierung der Bestätigungen."""
        active_count = 0
        for b in self.bookings:
            if b["active"]:
                if active_count < self.capacity:
                    b["confirmed"] = True
                    active_count += 1
                else:
                    b["confirmed"] = False

    def confirmed(self):
        """Liefert die Namen der bestätigten Buchungen in Buchungsreihenfolge."""
        return [b["name"] for b in self.bookings if b["active"] and b["confirmed"]]

    def waiting(self):
        """Liefert die Namen der wartenden Buchungen in Buchungsreihenfolge."""
        return [b["name"] for b in self.bookings if b["active"] and not b["confirmed"]]
