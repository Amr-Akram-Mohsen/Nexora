# app/integrations/enrichment/brand_detector.py
def detect_brands(text: str, brands_list: list[dict]) -> list[str]:
    """
    Detect brands in text using taxonomy data (name + aliases).
    Returns list of canonical brand names.
    """
    if not text:
        return []

    import re
    text_lower = text.lower()
    detected = set()

    for brand_data in brands_list:
        brand_name = brand_data["name"]
        aliases = brand_data.get("aliases", [])
        
        # Combine brand name and aliases into one search list
        patterns = [brand_name.lower()] + [a.lower() for a in aliases]
        
        for p in patterns:
            # Use regex for word boundaries to avoid partial matches
            if re.search(rf"\b{re.escape(p)}\b", text_lower):
                detected.add(brand_name)
                break

    return list(detected)
