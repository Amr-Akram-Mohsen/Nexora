from sqlalchemy import select, update
import difflib
from app.core.extensions import db
from app.domains.taxonomy.models import Category, Brand, Topic, Section, AttributeFacet
from app.domains.content.models import Content
from app.domains.item.models import Item

DOMAIN_MAP = {
    "categories": Category,
    "brands": Brand,
    "topics": Topic,
    "sections": Section,
    "attributes": AttributeFacet,
}

def detect_taxonomy_duplicates(domain: str, threshold: int = 85):
    if domain not in DOMAIN_MAP:
        raise ValueError("Invalid domain")
        
    model_class = DOMAIN_MAP[domain]
    records = db.session.execute(select(model_class)).scalars().all()
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
                duplicates.append({
                    "source": {"id": r2.id, "name": r2.name},
                    "target": {"id": r1.id, "name": r1.name},
                    "similarity": similarity
                })
                
    duplicates.sort(key=lambda x: x["similarity"], reverse=True)
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
        raise ValueError("Invalid domain")
        
    model_class = DOMAIN_MAP[domain]
    source = db.session.get(model_class, source_id)
    target = db.session.get(model_class, target_id)
    
    if not source or not target:
        raise ValueError("Entities not found")
        
    if domain == "categories":
        db.session.execute(update(Content).where(Content.category_id == source.id).values(category_id=target.id))
        db.session.execute(update(Item).where(Item.category_id == source.id).values(category_id=target.id))
        
    elif domain == "brands":
        from app.domains.relationships import content_brands
        _merge_m2m(content_brands, source.id, target.id, "brand_id")
        db.session.execute(update(Item).where(Item.brand_id == source.id).values(brand_id=target.id))
        
    elif domain == "topics":
        from app.domains.relationships import content_topics
        _merge_m2m(content_topics, source.id, target.id, "topic_id")
        
    elif domain == "sections":
        db.session.execute(update(Content).where(Content.section_id == source.id).values(section_id=target.id))
        
    elif domain == "attributes":
        from app.domains.relationships import content_attributes
        _merge_m2m(content_attributes, source.id, target.id, "attribute_id")

    db.session.delete(source)
    db.session.commit()
