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
            'id': booking_id,
            'name': name,
            'active': True
        })
        self.next_id += 1
        return booking_id

    def cancel(self, booking_id):
        """Storniert die Buchung mit der ID `booking_id`."""
        booking = next((b for b in self.bookings if b['id'] == booking_id), None)
        
        if booking is None or not booking['active']:
            raise ValueError("Booking ID not found or already cancelled.")
        
        booking['active'] = False

    def confirmed(self):
        """Liefert die Namen der bestätigten Buchungen in Buchungsreihenfolge."""
        active_bookings = [b for b in self.bookings if b['active']]
        confirmed = []
        count = 0
        
        for b in active_bookings:
            if count < self.capacity:
                confirmed.append(b['name'])
                count += 1
            else:
                break
        return confirmed

    def waiting(self):
        """Liefert die Namen der wartenden Buchungen in Buchungsreihenfolge."""
        active_bookings = [b for b in self.bookings if b['active']]
        waiting = []
        count = 0
        
        for b in active_bookings:
            if count < self.capacity:
                count += 1
            else:
                waiting.append(b['name'])
        return waiting
