import re
import logging

logger = logging.getLogger(__name__)

def safe_float(val, default=0.0):
    """
    Safely convert input to float.
    
    Handles:
    - None
    - Empty strings
    - Numeric strings
    - Formatted numbers ("1,23,456.78" or "1.234.567,89")
    - Currency symbols ("₹", "$", "€")
    - Invalid strings ("N/A", "Unknown", etc.)
    """
    if val is None:
        return default
        
    if isinstance(val, (int, float)):
        return float(val)
        
    try:
        # 1. Clean string: remove currency symbols and whitespace
        s = str(val).strip()
        # Remove common currency symbols and other non-numeric chars except digits, dot, comma and minus
        s = re.sub(r'[^\d.,\-]', '', s)
        
        if not s:
            return default
            
        # 2. Handle European/Indian formatting:
        # If there are multiple dots and one comma at the end, it's 1.234.567,89 -> 1234567.89
        if s.count('.') > 0 and s.count(',') == 1:
            s = s.replace('.', '').replace(',', '.')
        # If there are multiple commas and one dot at the end, it's 1,234,567.89 -> 1234567.89
        elif s.count(',') > 0 and s.count('.') == 1:
            s = s.replace(',', '')
        # If there's only a comma and no dot, check if it's likely a decimal (e.g., "12,34") or thousands ("1,234")
        elif ',' in s and '.' not in s:
            # Simple heuristic: if comma is 3 digits from right, treat as thousands separator unless it's the only punctuation
            parts = s.split(',')
            if len(parts[-1]) == 2: # Likely "12,34"
                s = s.replace(',', '.')
            else: # Likely "1,234"
                s = s.replace(',', '')
        
        return float(s)
    except (ValueError, TypeError):
        logger.warning("safe_float_failure: could not convert '%s' to float, using default %s", val, default)
        return default

def safe_int_percent(val, default_float=0.9):
    """
    Bonus: Safely convert input to an integer percentage (0-100).
    Uses safe_float as the base.
    """
    confidence = safe_float(val, default_float)
    return int(round(confidence * 100))
