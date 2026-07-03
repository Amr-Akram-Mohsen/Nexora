from sqlalchemy import select, func
from app.core.extensions import db
from app.domains.content.models import Content
from app.domains.item.models import Item
from app.domains.taxonomy.models import Category

def get_category_metrics(category_ids: list[int]) -> dict:
    if not category_ids: return {}
    content_counts = dict(db.session.execute(select(Content.category_id, func.count(Content.id)).where(Content.category_id.in_(category_ids)).group_by(Content.category_id)).all())
    item_counts = dict(db.session.execute(select(Item.category_id, func.count(Item.id)).where(Item.category_id.in_(category_ids)).group_by(Item.category_id)).all())
    children_counts = dict(db.session.execute(select(Category.parent_id, func.count(Category.id)).where(Category.parent_id.in_(category_ids)).group_by(Category.parent_id)).all())
    return {cid: {
        "content_count": content_counts.get(cid, 0), 
        "item_count": item_counts.get(cid, 0), 
    } for cid in category_ids}

def get_brand_metrics(brand_ids: list[int]) -> dict:
    if not brand_ids: return {}
    from app.domains.relationships import content_brands
    content_counts = dict(db.session.execute(select(content_brands.c.brand_id, func.count(content_brands.c.content_id)).where(content_brands.c.brand_id.in_(brand_ids)).group_by(content_brands.c.brand_id)).all())
    item_counts = dict(db.session.execute(select(Item.brand_id, func.count(Item.id)).where(Item.brand_id.in_(brand_ids)).group_by(Item.brand_id)).all())
    return {bid: {
        "content_count": content_counts.get(bid, 0), 
        "item_count": item_counts.get(bid, 0)
    } for bid in brand_ids}

def get_topic_metrics(topic_ids: list[int]) -> dict:
    if not topic_ids: return {}
    from app.domains.relationships import content_topics
    content_counts = dict(db.session.execute(select(content_topics.c.topic_id, func.count(content_topics.c.content_id)).where(content_topics.c.topic_id.in_(topic_ids)).group_by(content_topics.c.topic_id)).all())
    cat_spread_query = select(content_topics.c.topic_id, func.count(func.distinct(Content.category_id))).join(Content, Content.id == content_topics.c.content_id).where(content_topics.c.topic_id.in_(topic_ids)).group_by(content_topics.c.topic_id)
    category_spread = dict(db.session.execute(cat_spread_query).all())
    return {tid: {
        "content_count": content_counts.get(tid, 0),
        "category_spread": category_spread.get(tid, 0)
    } for tid in topic_ids}

def get_section_metrics(section_ids: list[int]) -> dict:
    if not section_ids: return {}
    content_counts = dict(db.session.execute(select(Content.section_id, func.count(Content.id)).where(Content.section_id.in_(section_ids)).group_by(Content.section_id)).all())
    cat_spread_query = select(Content.section_id, func.count(func.distinct(Content.category_id))).where(Content.section_id.in_(section_ids)).group_by(Content.section_id)
    category_spread = dict(db.session.execute(cat_spread_query).all())
    return {sid: {
        "content_count": content_counts.get(sid, 0),
        "category_spread": category_spread.get(sid, 0)
    } for sid in section_ids}

def get_attribute_metrics(attribute_ids: list[int]) -> dict:
    if not attribute_ids: return {}
    from app.domains.relationships import content_attributes
    content_counts = dict(db.session.execute(select(content_attributes.c.attribute_id, func.count(content_attributes.c.content_id)).where(content_attributes.c.attribute_id.in_(attribute_ids)).group_by(content_attributes.c.attribute_id)).all())
    return {aid: {
        "content_count": content_counts.get(aid, 0)
    } for aid in attribute_ids}

def get_facet_metrics(facet_ids: list[int], field_name: str) -> dict:
    if not facet_ids: return {}
    field = getattr(Content, field_name)
    content_counts = dict(db.session.execute(select(field, func.count(Content.id)).where(field.in_(facet_ids)).group_by(field)).all())
    return {fid: {
        "content_count": content_counts.get(fid, 0)
    } for fid in facet_ids}
