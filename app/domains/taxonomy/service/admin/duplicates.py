from sqlalchemy import select, update
import difflib
from app.core.extensions import db
from app.domains.taxonomy.models import Category, Brand, Entity, Section, AttributeFacet
from app.domains.content.models import Content
from app.domains.product.models import Product
DOMAIN_MAP = {'categories': Category, 'brands': Brand, 'topics': Entity, 'sections': Section, 'attributes': AttributeFacet}

def detect_taxonomy_duplicates(domain: str, threshold: int=85):
    if domain not in DOMAIN_MAP:
        raise ValueError('Invalid domain')
    model_class = DOMAIN_MAP[domain]
    stmt = select(model_class)
    if domain == 'topics':
        stmt = stmt.where(model_class.entity_type.in_(['topic', 'tag', 'concept']))
    records = db.session.execute(stmt).scalars().all()
    duplicates = []
    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            r1 = records[i]
            r2 = records[j]
            s1 = r1.name.lower().strip()
            s2 = r2.name.lower().strip()
            if s1 == s2:
                similarity = 100
            else:
                similarity = int(difflib.SequenceMatcher(None, s1, s2).ratio() * 100)
            if similarity > threshold:
                duplicates.append({'source': {'id': r2.id, 'name': r2.name}, 'target': {'id': r1.id, 'name': r1.name}, 'similarity': similarity})
    duplicates.sort(key=lambda x: x['similarity'], reverse=True)
    return duplicates[:50]

def _merge_m2m(association, source_id, target_id, relation_col_name):
    rel_col = getattr(association.c, relation_col_name)
    content_col = association.c.content_id
    content_ids = db.session.scalars(select(content_col).where(rel_col == source_id)).all()
    for cid in content_ids:
        exists = db.session.scalar(select(content_col).where(rel_col == target_id, content_col == cid))
        if not exists:
            db.session.execute(association.insert().values(content_id=cid, **{relation_col_name: target_id}))
    db.session.execute(association.delete().where(rel_col == source_id))

def merge_taxonomy_entities(domain: str, source_id: int, target_id: int):
    if domain not in DOMAIN_MAP:
        raise ValueError('Invalid domain')
    model_class = DOMAIN_MAP[domain]
    source = db.session.get(model_class, source_id)
    target = db.session.get(model_class, target_id)
    if not source or not target:
        raise ValueError('Entities not found')
    if domain == 'categories':
        db.session.execute(update(Content).where(Content.category_id == source.id).values(category_id=target.id))
        db.session.execute(update(Product).where(Product.category_id == source.id).values(category_id=target.id))
    elif domain == 'brands':
        from app.domains.relationships import ContentEntity
        db.session.execute(update(Product).where(Product.brand_id == source.id).values(brand_id=target.id))
        source_entity = db.session.execute(select(Entity).where(Entity.slug == source.slug)).scalar()
        target_entity = db.session.execute(select(Entity).where(Entity.slug == target.slug)).scalar()
        if source_entity and target_entity:
            _merge_m2m(ContentEntity.__table__, source_entity.id, target_entity.id, 'entity_id')
            db.session.delete(source_entity)
    elif domain == 'topics':
        from app.domains.relationships import ContentEntity
        _merge_m2m(ContentEntity.__table__, source.id, target.id, 'entity_id')
    elif domain == 'sections':
        db.session.execute(update(Content).where(Content.section_id == source.id).values(section_id=target.id))
    elif domain == 'attributes':
        from app.domains.relationships import content_attributes
        _merge_m2m(content_attributes, source.id, target.id, 'attribute_id')
    db.session.delete(source)
    db.session.commit()