from sqlalchemy import select, func, desc
from app.core.extensions import db

def get_taxonomy_intelligence():
    """
    Returns taxonomy concentration, category health, and tag coverage.
    """
    from app.domains.taxonomy.models import Category, Tag
    from app.domains.content.models import Content
    from app.domains.relationships import content_tags
    
    stmt_tags = select(
        Tag.name,
        func.count(content_tags.c.content_id).label('content_count')
    ).select_from(Tag)\
     .outerjoin(content_tags, Tag.id == content_tags.c.tag_id)\
     .group_by(Tag.id, Tag.name)\
     .order_by(desc('content_count'))\
     .limit(10)
     
    tag_rows = db.session.execute(stmt_tags).all()
    topic_concentration = [
        {"topic": r.name, "volume": r.content_count}
        for r in tag_rows
    ]
    
    stmt_cats = select(
        Category.id,
        Category.name,
        func.count(Content.id).label('content_count'),
        func.sum(Content.view_count + Content.like_count + Content.save_count).label('total_eng')
    ).select_from(Category)\
     .outerjoin(Content, Content.category_id == Category.id)\
     .group_by(Category.id, Category.name)\
     .having(func.count(Content.id) > 0)\
     .order_by(desc('total_eng'))
     
    cat_rows = db.session.execute(stmt_cats).all()
    category_health = []
    for r in cat_rows:
        count = r.content_count or 1
        eng = r.total_eng or 0
        avg_eng = round(eng / count, 1)
        category_health.append({
            "category": r.name,
            "volume": r.content_count,
            "avg_engagement": avg_eng
        })
        
    return {
        "topic_concentration": topic_concentration,
        "category_health": category_health
    }
