import datetime

def parse_date(text):
    """Liefert das Datum aus `text` (JJJJ-MM-TT) als datetime.date."""
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    
    try:
        # datetime.strptime prüft auf das Format JJJJ-MM-TT
        # %y wäre 2-stellig, %Y ist 4-stellig.
        # Da wir exakt JJJJ-MM-TT wollen, nutzen wir %Y-%m-%d.
        # strptime erlaubt aber oft auch Werte ohne führende Nullen, 
        # daher prüfen wir die Länge und das Format manuell.
        
        if len(text) != 10:
            raise ValueError("Invalid length")
            
        # Sicherstellen, dass Bindestriche an den richtigen Stellen stehen
        if text[4] != '-' or text[7] != '-':
            raise ValueError("Invalid format")
            
        # Sicherstellen, dass alle anderen Zeichen Ziffern sind
        parts = text.split('-')
        if not (parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit()):
            raise ValueError("Non-numeric characters")

        # datetime.date validiert die Existenz des Datums (z.B. kein 30. Februar)
        return datetime.datetime.strptime(text, "%Y-%m-%d").date()
        
    except (ValueError, IndexError):
        raise ValueError("Invalid date format or value")
