from app.domains.content.service import (
    get_content_by_id,
    get_related_contents,
    get_trending_contents,
    resolve_content_target
)
from app.domains.interaction.service import record_view
from app.shared.constants.core import TargetType

def get_article_page_data(content_id, user, ip_address):
    """
    Orchestrates data for a single content/article page.
    """
    content = get_content_by_id(content_id)
    if not content:
        return None

    # Resolve target (external link or internal item)
    resolve_content_target(content)

    # Record view interaction
    record_view(
        target=content,
        target_type=TargetType.CONTENT,
        user=user,
        ip_address=ip_address
    )

    related_contents = get_related_contents(content.id)
    trending_contents = get_trending_contents(limit=6, days=7, section_ids=[content.section_id])

    return {
        "content": content,
        "related_contents": related_contents,
        "trending_contents": trending_contents
    }
