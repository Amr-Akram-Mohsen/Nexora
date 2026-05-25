from app.domains.content.service import get_content_by_id
from app.application.content.query_service import (
    get_related_contents_cached,
    get_trending_contents_cached,
)
from app.domains.interaction.service import record_view
from app.infrastructure import cache
from app.shared.constants.core import TargetType


@cache.memoize(timeout=1800)
def get_content_page_static_data(content_id):
    from app.core.extensions import db

    return get_content_by_id(db.session, content_id)


def get_content_page_data(content_id):
    """
    Orchestrates data for a single content/article page.
    """
    content = get_content_page_static_data(content_id)
    # content is now a serialized dictionary
    if not content:
        return None

    related_contents = get_related_contents_cached(content["id"])

    # section is a serialized dict as well
    section_ids = [content["section_id"]] if content.get("section_id") else None
    trending_contents = get_trending_contents_cached(
        limit=6, days=7, section_ids=section_ids
    )

    return {
        "content": content,
        "related_contents": related_contents,
        "trending_contents": trending_contents,
    }


def record_content_view(content_id, user, ip_address):
    """
    Records an article/content view interaction.
    """
    record_view(
        target_id=content_id,
        target_type=TargetType.CONTENT,
        user=user,
        ip_address=ip_address,
    )
