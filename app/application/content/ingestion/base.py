# app/domains/content/ingestion/base.py
import logging
from sqlalchemy.exc import IntegrityError
from app.shared.utils.logging import log_item_skipped
from .taxonomy import resolve_taxonomy
from app.domains.content.service.command import apply_relationships
from app.domains.content.service.content_access import create_content, get_or_create_content

logger = logging.getLogger(__name__)

def generic_ingest(session, object_type, raw_data, model_class, factory_func):
    """
    Standardized ingestion flow for any content type.
    """
    try:
        # Wrap the item ingestion in a nested transaction (SAVEPOINT)
        with session.begin_nested():
            # 1. Deduplication and Model Creation
            obj, is_new = get_or_create_content(
                session,
                object_type=object_type,
                external_id=raw_data.get("external_id"),
                obj_factory=lambda: factory_func(raw_data),
                title_fallback=raw_data.get("title"),
                url_fallback=raw_data.get("url"),
                canonical_url=raw_data.get("canonical_url")
            )

            if not obj:
                return None, "skipped"

            # 2. Resolve Taxonomy (Section/Category)
            section, category = resolve_taxonomy(raw_data, session)

            # 3. Create/Link to Content Wrapper
            content, was_content_updated = create_content(
                session,
                obj=obj,
                object_type=object_type,
                published_at=raw_data.get("published_at"),
                category_id=category.id,
                section_id=section.id,
                is_published=raw_data.get("is_published", False)
            )

            # 4. Apply Relationships (Topics, Brands, Facets)
            updated_relationships = {}
            if content:
                updated_relationships = apply_relationships(session, content, raw_data)

            if is_new:
                return content, "created"
            
            if updated_relationships:
                return content, updated_relationships
            
            # If it's not new and nothing changed, it's effectively a skipped duplicate
            return None, "skipped"

    except IntegrityError:
        # The SAVEPOINT is automatically rolled back by the context manager.
        # The parent session transaction remains unpoisoned.
        log_item_skipped(
            logger, 
            source=raw_data.get("source", "unknown"),
            title=raw_data.get("title", "untitled"),
            reason="duplicate_integrity_error",
            external_id=raw_data.get("external_id")
        )
        return None, "skipped"
    except Exception as e:
        # The SAVEPOINT is automatically rolled back.
        # We re-raise to let the workflow handle non-integrity exceptions.
        logger.error("[INGEST] critical_failure  type=%s  err=%s", object_type, e)
        raise
