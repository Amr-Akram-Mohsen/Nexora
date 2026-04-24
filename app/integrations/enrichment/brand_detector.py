# app/integrations/enrichment/brand_detector.py
def detect_brands(text: str, brand_aliases: dict) -> list[str]:
    """
    Detect brands in text using alias mapping.
    Returns list of canonical brand names.
    """
    if not text:
        return []

    text_lower = text.lower()
    detected = set()

    for brand, aliases in brand_aliases.items():
        # Direct brand match
        if f" {brand.lower()} " in f" {text_lower} ":
            detected.add(brand)
            continue

        # Alias match
        for alias in aliases:
            if f" {alias.lower()} " in f" {text_lower} ":
                detected.add(brand)
                break

    return list(detected)

# and I already added section_slug and category_slug inside prepare_article function so