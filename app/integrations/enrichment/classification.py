# app/integrations/enrichment/classification.py
import logging
from app.integrations.enrichment.brand_detector import detect_brands
from app.integrations.enrichment.facet_detector import detect_facets
from app.shared.constants.taxonomy import TAXONOMY
from app.shared.utils.logging import log_integration_start, log_integration_success, log_integration_error

logger = logging.getLogger(__name__)

_NAME = "classification"

from typing import Union
from app.shared.dto.ingestion import RawItemDTO, ClassifiedItemDTO


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

        log_integration_start(
            logger, _NAME,
            section=section_slug,
            category=category_slug,
            title=title[:60],
        )

        # 1. Classification (deterministic from query)
        data["section_slug"] = section_slug
        data["category_slug"] = category_slug

        # 2. Topics (from discovery query context)
        data["topic_slugs"] = q_obj.get("topics", [])

        # 3. Brands (merge query-pinned brands + auto-detected brands)
        detected_brands = detect_brands(text_blob, TAXONOMY.get("brands", []))
        data["brand_slugs"] = list(set(q_obj.get("brands", []) + detected_brands))

        # 4. Facets (intent, gender, etc.)
        query_intent = q_obj.get("intent")
        data["facets"] = detect_facets(title, description, category_slug, query_intent=query_intent)

        # 5. Metadata Traceability
        if q_obj.get("region"):
            data["region"] = q_obj["region"]
        if q_obj.get("query"):
            data["discovery_query"] = q_obj["query"]

        result = ClassifiedItemDTO(**data)
        log_integration_success(
            logger, _NAME, items=1,
            brands=len(result.brand_slugs),
            facets=list(result.facets.keys()),
        )
        return result

    except Exception as e:
        log_integration_error(logger, _NAME, e, title=title[:60], exc_info=True)
        # Re-raise so the workflow can decide whether to skip this item
        raise
