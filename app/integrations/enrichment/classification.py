# app/integrations/enrichment/classification.py
import logging
from app.integrations.enrichment.brand_detector import detect_brands
from app.integrations.enrichment.facet_detector import detect_facets
from app.shared.constants.taxonomy import TAXONOMY

logger = logging.getLogger(__name__)

def classify_content_metadata(raw: dict, section_slug: str, category_slug: str, q_obj: dict) -> dict:
    """
    Metadata Enrichment / Classification step for all content types.
    - Merges query-based classification (Section/Category)
    - Detects brands from title/description
    - Detects facets (intent, gender, price tier)
    - Attaches region and discovery query context
    """
    title = raw.get("title") or ""
    description = raw.get("description") or ""
    text_blob = f"{title}. {description}"

    # 1. Classification (deterministic from query)
    raw["section_slug"] = section_slug
    raw["category_slug"] = category_slug

    # 2. Topics (from discovery query context)
    raw["topic_slugs"] = q_obj.get("topics", [])

    # 3. Brands (merge query-pinned brands + auto-detected brands)
    detected_brands = detect_brands(text_blob, TAXONOMY.get("brands", []))
    raw["brand_slugs"] = list(set(q_obj.get("brands", []) + detected_brands))

    # 4. Facets (intent, gender, etc.)
    query_intent = q_obj.get("intent")
    raw["facets"] = detect_facets(title, description, category_slug, query_intent=query_intent)

    # 5. Metadata Traceability
    if q_obj.get("region"):
        raw["region"] = q_obj["region"]
    if q_obj.get("query"):
        raw["discovery_query"] = q_obj["query"]

    return raw
