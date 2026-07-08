from sqlalchemy import select, func
from app.core.extensions import db
from app.domains.taxonomy.models import Category, Brand, Topic, Section
from app.domains.content.models import Content
from app.domains.item.models import Item

def _generate_suggestions_for_entities(unmapped_content, entities, entity_type):
    suggestions = []
    for c in unmapped_content:
        if not c.title: continue
        title_lower = f" {c.title.lower()} "
        for ent in entities:
            if f" {ent.name.lower()} " in title_lower:
                suggestions.append({
                    "content_id": c.id,
                    "content_title": c.title,
                    "type": entity_type,
                    "suggested_id": ent.id,
                    "suggested_name": ent.name
                })
                break
    return suggestions

def get_taxonomy_insights_suggestions(limit: int = 50):
    from app.domains.relationships import content_brands
    
    unmapped_brand = db.session.execute(
        select(Content).where(
            ~db.session.query(content_brands.c.brand_id).filter(content_brands.c.content_id == Content.id).exists()
        ).order_by(Content.id.desc()).limit(200)
    ).scalars().all()
    
    unmapped_cat = db.session.execute(
        select(Content).where(Content.category_id == None).order_by(Content.id.desc()).limit(200)
    ).scalars().all()

    brands = db.session.execute(select(Brand)).scalars().all()
    categories = db.session.execute(select(Category)).scalars().all()
    
    suggestions = []
    suggestions.extend(_generate_suggestions_for_entities(unmapped_brand, brands, "Brand"))
    suggestions.extend(_generate_suggestions_for_entities(unmapped_cat, categories, "Category"))

    return suggestions[:limit]


def get_taxonomy_insights_coherence(limit: int = 50):
    from app.domains.relationships import content_items
    
    from sqlalchemy.orm import selectinload
    contents = db.session.execute(
        select(Content)
        .options(selectinload(Content.brands))
        .where(
            db.session.query(content_items.c.item_id).filter(content_items.c.content_id == Content.id).exists()
        ).order_by(Content.id.desc()).limit(100)
    ).scalars().all()
    
    conflicts = []
    for c in contents:
        items = db.session.execute(
            select(Item)
            .options(selectinload(Item.brand))
            .join(content_items, content_items.c.item_id == Item.id)
            .where(content_items.c.content_id == c.id)
        ).scalars().all()
        
        if not items: continue
        
        content_brand_ids = {b.id for b in c.brands}
        
        for item in items:
            if item.brand_id and content_brand_ids and item.brand_id not in content_brand_ids:
                conflicts.append({
                    "content_id": c.id,
                    "content_title": c.title,
                    "content_brands": [b.name for b in c.brands],
                    "item_id": item.id,
                    "item_name": item.name,
                    "item_brand": item.brand.name if item.brand else "Unknown",
                    "suggested_brand_id": item.brand_id
                })
                
    return conflicts[:limit]


def apply_taxonomy_insight(content_id: int, type_: str, suggested_id: int):
    content = db.session.get(Content, content_id)
    if not content:
        raise ValueError("Content not found")
        
    if type_ == "Brand":
        from app.domains.relationships import content_brands
        exists = db.session.scalar(select(content_brands.c.content_id).where(content_brands.c.content_id == content_id, content_brands.c.brand_id == suggested_id))
        if not exists:
            db.session.execute(content_brands.insert().values(content_id=content_id, brand_id=suggested_id))
    elif type_ == "Category":
        content.category_id = suggested_id
        
    db.session.commit()
