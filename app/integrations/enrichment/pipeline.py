from app.integrations.enrichment.brand_detector import detect_brands
from app.integrations.enrichment.facet_detector import detect_facets
from app.shared.constants.taxonomy import TAXONOMY


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
    detected_brands = detect_brands(text_blob, TAXONOMY.get("brands", []))
    raw["brand_slugs"] = list(set(q_obj.get("brands", []) + detected_brands))

    # 4. Facets
    # Prefer intent from the query if available
    query_intent = q_obj.get("intent")
    raw["facets"] = detect_facets(title, description, category_slug, query_intent=query_intent)

    # 5. Region (from query/scraper context)
    if q_obj.get("region"):
        raw["region"] = q_obj["region"]

    # 6. Discovery Context
    if q_obj.get("query"):
        raw["discovery_query"] = q_obj["query"]

    # 7. Premium Metadata: Reading Time
    content_text = raw.get("content") or description or ""
    # word_count = len(content_text.split())
    # raw["reading_time_min"] = max(1, word_count // 200)

    return raw
