from ...models import Content
from sqlalchemy import func, case
from ..content_access import assign_target_to_contents

def get_related_contents(session, content_id, limit=6):
    from .options import CONTENT_EAGER_LOADS
    from app.domains.system.models import Category, Section, Topic, Brand
    content = session.query(Content).options(*CONTENT_EAGER_LOADS).get(content_id)
    if not content: return []
    topic_ids = [t.id for t in content.topics]
    brand_ids = [b.id for b in content.brands]
    section_id = content.section_id

    relevance_score = (
        case((Topic.id.in_(topic_ids), 3), else_=0) +
        case((Brand.id.in_(brand_ids), 2), else_=0) +
        case((Category.id.in_([content.category_id]), 1), else_=0)
    )

    query = (
        session.query(
            Content,
            func.sum(relevance_score).label("score")
        )
        .join(Content.section)
        .filter(Section.id == section_id)
        .outerjoin(Content.topics)
        .outerjoin(Content.brands)
        .outerjoin(Content.category)
        .filter(Content.id != content.id)
        .group_by(Content.id)
        .having(func.sum(relevance_score) > 0)
        .order_by(
            func.sum(relevance_score).desc(),
            Content.published_at.desc()
        )
        .options(*CONTENT_EAGER_LOADS)
        .limit(limit)
    )

    rows = query.all()
    contents = [row.Content for row in rows]
    return assign_target_to_contents(contents, session)
