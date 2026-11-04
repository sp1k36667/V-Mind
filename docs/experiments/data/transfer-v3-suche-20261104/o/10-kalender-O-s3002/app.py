class Calendar:
    """Reservierungen eines Raums an einem Tag."""

    def __init__(self):
        self.reservations = []

    def reserve(self, start_min, end_min):
        """Reserviert den Zeitraum; True bei Erfolg, False bei Überschneidung."""
        if not (0 <= start_min <= 1440 and 0 <= end_min <= 1440):
            raise ValueError("Zeit muss zwischen 0 und 1440 liegen.")
        if start_min >= end_min:
            raise ValueError("Startzeit muss vor Endzeit liegen.")

        for start, end in self.reservations:
            if not (end_min <= start or start_min >= end):
                return False
        
        self.reservations.append((start_min, end_min))
        return True

    def bookings(self):
        """Liefert alle Reservierungen nach Beginn sortiert: [(start_min, end_min), ...]."""
        return sorted(self.reservations)
