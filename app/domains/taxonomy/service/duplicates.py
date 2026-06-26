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
        content_ids = db.session.scalars(select(content_brands.c.content_id).where(content_brands.c.brand_id == source.id)).all()
        for cid in content_ids:
            exists = db.session.scalar(select(content_brands.c.content_id).where(content_brands.c.brand_id == target.id, content_brands.c.content_id == cid))
            if not exists:
                db.session.execute(content_brands.insert().values(content_id=cid, brand_id=target.id))
        db.session.execute(content_brands.delete().where(content_brands.c.brand_id == source.id))
        db.session.execute(update(Item).where(Item.brand_id == source.id).values(brand_id=target.id))
        
    elif domain == "topics":
        from app.domains.relationships import content_topics
        content_ids = db.session.scalars(select(content_topics.c.content_id).where(content_topics.c.topic_id == source.id)).all()
        for cid in content_ids:
            exists = db.session.scalar(select(content_topics.c.content_id).where(content_topics.c.topic_id == target.id, content_topics.c.content_id == cid))
            if not exists:
                db.session.execute(content_topics.insert().values(content_id=cid, topic_id=target.id))
        db.session.execute(content_topics.delete().where(content_topics.c.topic_id == source.id))
        
    elif domain == "sections":
        db.session.execute(update(Content).where(Content.section_id == source.id).values(section_id=target.id))
        
    elif domain == "attributes":
        from app.domains.relationships import content_attributes
        content_ids = db.session.scalars(select(content_attributes.c.content_id).where(content_attributes.c.attribute_id == source.id)).all()
        for cid in content_ids:
            exists = db.session.scalar(select(content_attributes.c.content_id).where(content_attributes.c.attribute_id == target.id, content_attributes.c.content_id == cid))
            if not exists:
                db.session.execute(content_attributes.insert().values(content_id=cid, attribute_id=target.id))
        db.session.execute(content_attributes.delete().where(content_attributes.c.attribute_id == source.id))

    db.session.delete(source)
    db.session.commit()
