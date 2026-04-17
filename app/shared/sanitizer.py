import re
import html

def sanitize_text(text):
    """
    Cleans up common API/scraped content junk.
    """
    if not text or not isinstance(text, str):
        return text
    
    # 1. Unescape HTML entities (e.g. &amp; -> &)
    text = html.unescape(text)
    
    # 2. Strip HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # 3. Handle specific noisy Unicode common in e-commerce
    # Replace non-breaking dashes/spaces with regular ones
    replacements = {
        '\u2011': '-',  # Non-breaking hyphen
        '\u2013': '-',  # En dash
        '\u2014': '-',  # Em dash
        '\u2010': '-',  # Hyphen
        '\u00a0': ' ',  # Non-breaking space
        '\u202f': ' ',  # Narrow non-breaking space
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
        
    # 4. Collapse multiple spaces and trim
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def sanitize_json(data):
    """
    Recursively sanitizes values in a dictionary or list.
    """
    if isinstance(data, dict):
        return {k: sanitize_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_json(v) for v in data]
    else:
        return sanitize_text(data)
