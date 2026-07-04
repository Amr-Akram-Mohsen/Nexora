from sqlalchemy import select, func
from app.core.extensions import db
from app.domains.content.models import Content
from app.domains.item.models import Item
from app.domains.taxonomy.models import Category

def _get_metric_counts(fk_col, ids):
    if not ids: return {}
    rows = db.session.execute(
        select(fk_col, func.count()).where(fk_col.in_(ids)).group_by(fk_col)
    ).all()
    return dict(rows)

def get_category_metrics(category_ids: list[int]) -> dict:
    if not category_ids: return {}
    content_counts = _get_metric_counts(Content.category_id, category_ids)
    item_counts = _get_metric_counts(Item.category_id, category_ids)
    return {cid: {
        "content_count": content_counts.get(cid, 0), 
        "item_count": item_counts.get(cid, 0), 
    } for cid in category_ids}

def get_brand_metrics(brand_ids: list[int]) -> dict:
    if not brand_ids: return {}
    from app.domains.relationships import content_brands
    content_counts = _get_metric_counts(content_brands.c.brand_id, brand_ids)
    item_counts = _get_metric_counts(Item.brand_id, brand_ids)
    return {bid: {
        "content_count": content_counts.get(bid, 0), 
        "item_count": item_counts.get(bid, 0)
    } for bid in brand_ids}

def get_topic_metrics(topic_ids: list[int]) -> dict:
    if not topic_ids: return {}
    from app.domains.relationships import content_topics
    content_counts = _get_metric_counts(content_topics.c.topic_id, topic_ids)
    cat_spread_query = select(content_topics.c.topic_id, func.count(func.distinct(Content.category_id))).join(Content, Content.id == content_topics.c.content_id).where(content_topics.c.topic_id.in_(topic_ids)).group_by(content_topics.c.topic_id)
    category_spread = dict(db.session.execute(cat_spread_query).all())
    return {tid: {
        "content_count": content_counts.get(tid, 0),
        "category_spread": category_spread.get(tid, 0)
    } for tid in topic_ids}

def get_section_metrics(section_ids: list[int]) -> dict:
    if not section_ids: return {}
    content_counts = _get_metric_counts(Content.section_id, section_ids)
    cat_spread_query = select(Content.section_id, func.count(func.distinct(Content.category_id))).where(Content.section_id.in_(section_ids)).group_by(Content.section_id)
    category_spread = dict(db.session.execute(cat_spread_query).all())
    return {sid: {
        "content_count": content_counts.get(sid, 0),
        "category_spread": category_spread.get(sid, 0)
    } for sid in section_ids}

def get_attribute_metrics(attribute_ids: list[int]) -> dict:
    if not attribute_ids: return {}
    from app.domains.relationships import content_attributes
    content_counts = _get_metric_counts(content_attributes.c.attribute_id, attribute_ids)
    return {aid: {
        "content_count": content_counts.get(aid, 0)
    } for aid in attribute_ids}

def get_facet_metrics(facet_ids: list[int], field_name: str) -> dict:
    if not facet_ids: return {}
    field = getattr(Content, field_name)
    content_counts = _get_metric_counts(field, facet_ids)
    return {fid: {
        "content_count": content_counts.get(fid, 0)
    } for fid in facet_ids}
