# app/integrations/enrichment/brand_detector.py
def detect_brands(text: str, brand_aliases: dict) -> list[str]:
    """
    Detect brands in text using alias mapping.
    Returns list of canonical brand names.
    """
    if not text:
        return []

    import re
    text_lower = text.lower()
    detected = set()

    for brand, aliases in brand_aliases.items():
        # Combine brand name and aliases into one search list
        patterns = [brand.lower()] + [a.lower() for a in aliases]
        
        for p in patterns:
            # Use regex for word boundaries to avoid partial matches (e.g., "Apple" in "Pineapple")
            if re.search(rf"\b{re.escape(p)}\b", text_lower):
                detected.add(brand)
                break

    return list(detected)
