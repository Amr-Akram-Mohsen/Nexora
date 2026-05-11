from ...models import Content
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from app.shared.constants.core import TargetType
from ..content_access import assign_target_to_contents

def get_trending_contents(session, limit=6, days=7, section_ids=None):
    from .options import CONTENT_EAGER_LOADS
    from app.domains.system.models import Section
    from app.domains.interaction.models import View
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        session.query(
            Content,
            func.count(View.id).label("recent_views")
        )
        .join(View, (View.target_type == TargetType.CONTENT) & (View.target_id == Content.id))
        .filter(View.created_at >= cutoff, Content.is_published == True, Content.is_active == True)
    )

    if section_ids:
        query = query.join(Content.section).filter(Section.id.in_(section_ids))

    query = (
        query.group_by(Content.id)
        .order_by(func.count(View.id).desc(), Content.published_at.desc())
        .options(*CONTENT_EAGER_LOADS)
        .limit(limit)
    )

    rows = query.all()
    contents = [row.Content for row in rows]
    return assign_target_to_contents(contents, session)