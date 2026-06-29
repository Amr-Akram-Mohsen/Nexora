# app/integrations/enrichment/classification.py
import logging
from .brand_detector import detect_brands
from .facet_detector import detect_facets
from app.shared.constants.taxonomy import TAXONOMY
from app.shared.utils.logging import log_integration_error
from typing import Union
from app.shared.dto.ingestion import RawItemDTO, ClassifiedItemDTO

logger = logging.getLogger(__name__)

_NAME = "classification"


def classify_content_metadata(
    raw: Union[RawItemDTO, dict],
    section_slug: str,
    category_slug: str,
    q_obj: dict,
) -> ClassifiedItemDTO:
    """
    Metadata Enrichment / Classification step for all content types.
    - Merges query-based classification (Section/Category)
    - Detects brands from title/description
    - Detects facets (intent, gender, price tier)
    - Attaches region and discovery query context
    Always returns a ClassifiedItemDTO (never raises silently).
    """
    title = ""
    try:
        data = raw.model_dump() if hasattr(raw, "model_dump") else dict(raw)

        title = data.get("title") or ""
        description = data.get("description") or ""
        text_blob = f"{title}. {description}"

        logger.debug(
            "[INTEGRATION][%s] start  section=%s  category=%s  title=%.60s",
            _NAME,
            section_slug,
            category_slug,
            title,
        )

        # 1. Classification (deterministic from query)
        #    The workflow passes composite slugs like "electronics:smartphones".
        #    We store only the leaf ("smartphones") in category_slug so that
        #    the taxonomy resolver can find it in the DB by leaf slug.
        data["section_slug"] = section_slug
        # Strip parent prefix from composite discovery keys, e.g. "electronics:smartphones" → "smartphones"
        leaf_slug = category_slug.split(":")[-1] if ":" in category_slug else category_slug
        data["category_slug"] = leaf_slug
        # Keep the full composite key for traceability / debugging
        data["discovery_category"] = category_slug

        # 2. Topics (from discovery query context)
        data["topic_slugs"] = q_obj.get("topics", [])

        # 3. Brands (merge query-pinned brands + auto-detected brands)
        detected_brands = detect_brands(text_blob, TAXONOMY.get("brands", []))
        data["brand_slugs"] = list(set(q_obj.get("brands", []) + detected_brands))

        # 4. Facets (intent, gender, etc.)
        query_intent = q_obj.get("intent")
        data["facets"] = detect_facets(
            title, description, category_slug, query_intent=query_intent
        )

        # 5. Metadata Traceability & Regional Attributes
        region_val = data.get("region") or q_obj.get("region")
        if region_val:
            data["region"] = region_val
            region_attr = f"Region: {str(region_val).upper()}"
            if "attributes" not in data["facets"]:
                data["facets"]["attributes"] = []
            if region_attr not in data["facets"]["attributes"]:
                data["facets"]["attributes"].append(region_attr)
            
        if q_obj.get("query"):
            data["discovery_query"] = q_obj["query"]

        result = ClassifiedItemDTO(**data)
        logger.debug(
            "[INTEGRATION][%s] success  brands=%d  facets=%s",
            _NAME,
            len(result.brand_slugs),
            list(result.facets.keys()),
        )
        return result

    except Exception as e:
        log_integration_error(logger, _NAME, e, title=title[:60], exc_info=True)
        # Re-raise so the workflow can decide whether to skip this item
        raise
