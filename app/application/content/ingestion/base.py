# app/domains/content/ingestion/base.py
import logging
from sqlalchemy.exc import IntegrityError
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
                url_fallback=raw_data.get("url")
            )

            if not obj:
                return None, False

            # 2. Resolve Taxonomy (Section/Category)
            section, category = resolve_taxonomy(raw_data, session)

            # 3. Create/Link to Content Wrapper
            content = create_content(
                session,
                obj=obj,
                object_type=object_type,
                published_at=raw_data.get("published_at"),
                category_id=category.id,
                section_id=section.id
            )

            # 4. Apply Relationships (Topics, Brands, Facets)
            if content:
                apply_relationships(session, content, raw_data)

            return content, is_new

    except IntegrityError:
        # The SAVEPOINT is automatically rolled back by the context manager.
        # The parent session transaction remains unpoisoned.
        logger.info(f"Duplicate skipped: {object_type} - {raw_data.get('external_id')}")
        return None, False
    except Exception:
        # The SAVEPOINT is automatically rolled back.
        # We re-raise to let the workflow handle non-integrity exceptions.
        logger.exception(f"[Ingestion] Failed to ingest {object_type}")
        raise
