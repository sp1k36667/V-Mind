import datetime

def parse_date(text):
    """Liefert das Datum aus `text` (JJJJ-MM-TT) als datetime.date."""
    if not isinstance(text, str):
        raise ValueError("Eingabe muss ein String sein.")
    
    try:
        # Prüfen auf exakte Länge und Format (JJJJ-MM-TT)
        # Dies stellt sicher, dass keine Leerzeichen oder falsche Trenner vorhanden sind
        dt = datetime.datetime.strptime(text, "%Y-%m-%d")
        
        # strptime ist manchmal zu tolerant (z.B. 2026-1-5), 
        # daher prüfen wir die exakte String-Struktur
        if len(text) != 10 or text[4] != '-' or text[7] != '-':
            raise ValueError
            
        return dt.date()
    except ValueError:
        raise ValueError("Ungültiges Datumsformat. Erwartet: JJJJ-MM-TT.")
