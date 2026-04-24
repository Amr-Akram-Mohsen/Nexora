from app.integrations.enrichment.brand_detector import detect_brands
from app.integrations.enrichment.facet_detector import detect_facets
from app.shared.constants.brand_aliases import BRAND_ALIASES


def prepare_article(raw: dict, section_slug: str, category_slug: str, q_obj: dict) -> dict:
    """
    Central enrichment pipeline.
    - merges query-based classification
    - detects brands
    - detects facets
    """

    title = raw.get("title") or ""
    description = raw.get("description") or ""

    text_blob = f"{title}. {description}"

    # 1. Classification (deterministic)
    raw["section_slug"] = section_slug
    raw["category_slug"] = category_slug

    # 2. Topics (from query only)
    raw["topic_slugs"] = q_obj.get("topics", [])

    # 3. Brands (merge query + detected)
    detected_brands = detect_brands(text_blob, BRAND_ALIASES)
    raw["brand_slugs"] = list(set(q_obj.get("brands", []) + detected_brands))

    # 4. Facets (NEW)
    raw["facets"] = detect_facets(title, description, category_slug)

    return raw
