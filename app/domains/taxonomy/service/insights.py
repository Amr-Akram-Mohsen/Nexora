from sqlalchemy import select, func
from app.core.extensions import db
from app.domains.taxonomy.models import Category, Brand, Entity, Section
from app.domains.content.models import Content
from app.domains.product.models import Product

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
    from app.domains.relationships import ContentEntity
    
    unmapped_brand = db.session.execute(
        select(Content).where(
            ~db.session.query(ContentEntity.content_id).filter(ContentEntity.content_id == Content.id).join(Entity, Entity.id == ContentEntity.entity_id).filter(Entity.entity_type == 'brand').exists()
        ).order_by(Content.id.desc()).limit(200)
    ).scalars().all()
    
    unmapped_cat = db.session.execute(
        select(Content).where(Content.category_id == None).order_by(Content.id.desc()).limit(200)
    ).scalars().all()

    brands = db.session.execute(select(Entity).where(Entity.entity_type == 'brand')).scalars().all()
    categories = db.session.execute(select(Category)).scalars().all()
    
    suggestions = []
    suggestions.extend(_generate_suggestions_for_entities(unmapped_brand, brands, "Brand"))
    suggestions.extend(_generate_suggestions_for_entities(unmapped_cat, categories, "Category"))

    return suggestions[:limit]


def get_taxonomy_insights_coherence(limit: int = 50):
    from app.domains.relationships import content_products, ContentEntity
    
    from sqlalchemy.orm import selectinload
    contents = db.session.execute(
        select(Content)
        .options(selectinload(Content.content_entities).selectinload(ContentEntity.entity))
        .where(
            db.session.query(content_products.c.product_id).filter(content_products.c.content_id == Content.id).exists()
        ).order_by(Content.id.desc()).limit(100)
    ).scalars().all()
    
    conflicts = []
    for c in contents:
        products = db.session.execute(
            select(Product)
            .options(selectinload(Product.brand))
            .join(content_products, content_products.c.product_id == Product.id)
            .where(content_products.c.content_id == c.id)
        ).scalars().all()
        
        if not products: continue
        
        content_brand_ids = {ce.entity.id for ce in c.content_entities if ce.entity.entity_type == 'brand' or ce.entity.origin == 'legacy_brand'}
        
        for product in products:
            if product.brand:
                item_entity = db.session.execute(select(Entity).where(Entity.slug == product.brand.slug)).scalar()
                if item_entity and content_brand_ids and item_entity.id not in content_brand_ids:
                    conflicts.append({
                        "content_id": c.id,
                        "content_title": c.title,
                        "content_brands": [ce.entity.name for ce in c.content_entities if ce.entity.entity_type == 'brand' or ce.entity.origin == 'legacy_brand'],
                        "product_id": product.id,
                        "item_name": product.name,
                        "item_brand": product.brand.name if product.brand else "Unknown",
                        "suggested_brand_id": item_entity.id
                    })
                
    return conflicts[:limit]


def apply_taxonomy_insight(content_id: int, type_: str, suggested_id: int):
    content = db.session.get(Content, content_id)
    if not content:
        raise ValueError("Content not found")
        
    if type_ == "Brand":
        from app.domains.relationships import ContentEntity
        exists = db.session.scalar(select(ContentEntity.id).where(ContentEntity.content_id == content_id, ContentEntity.entity_id == suggested_id))
        if not exists:
            ce = ContentEntity(content_id=content_id, entity_id=suggested_id, origin="manual", confidence=1.0)
            db.session.add(ce)
    elif type_ == "Category":
        content.category_id = suggested_id
        
    db.session.commit()
