class Stock:
    """Bestand eines Artikels."""

    def __init__(self, initial):
        if not isinstance(initial, int) or initial < 0:
            raise ValueError("Initialer Bestand muss eine ganze Zahl >= 0 sein.")
        self._current_stock = initial

    def deposit(self, quantity):
        """Erhöht den Bestand um `quantity`."""
        if not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Einzahlung muss eine ganze Zahl >= 1 sein.")
        self._current_stock += quantity

    def withdraw(self, quantity):
        """Verringert den Bestand um `quantity`."""
        if not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Entnahme muss eine ganze Zahl >= 1 sein.")
        if quantity > self._current_stock:
            raise ValueError("Nicht genügend Bestand für Entnahme.")
        self._current_stock -= quantity

    def balance(self):
        """Liefert den aktuellen Bestand (int)."""
        return self._current_stock
