from sqlalchemy import select, func, or_
from app.core.extensions import db
from app.domains.taxonomy.models import Category, Brand, Topic, Section, AttributeFacet
from app.shared.utils.slug import generate_slug
from app.domains.content.models import Content
from app.domains.item.models import Item
from app.domains.relationships import content_brands, content_topics, content_attributes, ArticleSource
from app.domains.external.models import LastAPIFetch

def get_admin_categories_paginated(page, per_page, search="", status=None, health=None):
    stmt = select(Category).order_by(Category.name.asc())
    if search:
        stmt = stmt.where(Category.name.ilike(f"%{search}%"))
        
    if status == "1":
        stmt = stmt.where(Category.is_active == True)
    elif status == "0":
        stmt = stmt.where(Category.is_active == False)
        
    if health == "unused":
        stmt = stmt.where(
            ~db.session.query(Content.id).filter(Content.category_id == Category.id).exists()
        ).where(
            ~db.session.query(Item.id).filter(Item.category_id == Category.id).exists()
        )
    elif health == "inactive-linked":
        stmt = stmt.where(Category.is_active == False).where(
            db.session.query(Content.id).filter(Content.category_id == Category.id).exists() |
            db.session.query(Item.id).filter(Item.category_id == Category.id).exists()
        )
        
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)

def get_admin_brands_paginated(page, per_page, search="", status=None, health=None):
    stmt = select(Brand).order_by(Brand.name.asc())
    if search:
        stmt = stmt.where(Brand.name.ilike(f"%{search}%"))
        
    if status == "1":
        stmt = stmt.where(Brand.is_active == True)
    elif status == "0":
        stmt = stmt.where(Brand.is_active == False)
        
    if health == "unused":
        stmt = stmt.where(
            ~db.session.query(content_brands.c.content_id).filter(content_brands.c.brand_id == Brand.id).exists()
        ).where(
            ~db.session.query(Item.id).filter(Item.brand_id == Brand.id).exists()
        )
    elif health == "inactive-linked":
        stmt = stmt.where(Brand.is_active == False).where(
            db.session.query(content_brands.c.content_id).filter(content_brands.c.brand_id == Brand.id).exists() |
            db.session.query(Item.id).filter(Item.brand_id == Brand.id).exists()
        )
        
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)

def get_admin_topics_paginated(page, per_page, search="", status=None, health=None):
    stmt = select(Topic).order_by(Topic.name.asc())
    if search:
        stmt = stmt.where(Topic.name.ilike(f"%{search}%"))
        
    if status == "1":
        stmt = stmt.where(Topic.is_active == True)
    elif status == "0":
        stmt = stmt.where(Topic.is_active == False)
        
    if health == "unused":
        stmt = stmt.where(
            ~db.session.query(content_topics.c.content_id).filter(content_topics.c.topic_id == Topic.id).exists()
        )
    elif health == "inactive-linked":
        stmt = stmt.where(Topic.is_active == False).where(
            db.session.query(content_topics.c.content_id).filter(content_topics.c.topic_id == Topic.id).exists()
        )
        
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)

def get_admin_sections_paginated(page, per_page, search="", status=None, health=None):
    stmt = select(Section).order_by(Section.name.asc())
    if search:
        stmt = stmt.where(Section.name.ilike(f"%{search}%"))
        
    if status == "1":
        stmt = stmt.where(Section.is_active == True)
    elif status == "0":
        stmt = stmt.where(Section.is_active == False)
        
    if health == "unused":
        stmt = stmt.where(
            ~db.session.query(Content.id).filter(Content.section_id == Section.id).exists()
        )
    elif health == "inactive-linked":
        stmt = stmt.where(Section.is_active == False).where(
            db.session.query(Content.id).filter(Content.section_id == Section.id).exists()
        )
        
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)

def get_admin_attributes_paginated(page, per_page, search="", health=None):
    stmt = select(AttributeFacet).order_by(AttributeFacet.name.asc())
    if search:
        stmt = stmt.where(AttributeFacet.name.ilike(f"%{search}%"))
        
    if health == "unused":
        stmt = stmt.where(
            ~db.session.query(content_attributes.c.content_id).filter(content_attributes.c.attribute_id == AttributeFacet.id).exists()
        )
        
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)

def get_admin_facet_paginated(model_class, field_name, page, per_page, search="", health=None):
    stmt = select(model_class).order_by(model_class.name.asc())
    if search:
        stmt = stmt.where(model_class.name.ilike(f"%{search}%"))
    
    if health == "unused":
        field = getattr(Content, field_name)
        stmt = stmt.where(~db.session.query(Content.id).filter(field == model_class.id).exists())

    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


def get_admin_categories(search=""):
    stmt = select(Category).order_by(Category.name.asc())
    if search:
        stmt = stmt.where(Category.name.ilike(f"%{search}%"))
    return db.session.execute(stmt).scalars().all()

def create_admin_category(name, is_active=True):
    slug = generate_slug(name)
    if db.session.execute(select(Category).where(Category.slug == slug)).scalar_one_or_none():
        raise ValueError(f"Category with slug '{slug}' already exists")
    cat = Category(name=name, slug=slug, is_active=is_active)
    db.session.add(cat)
    return cat

def update_admin_category(cat_id, data):
    cat = db.session.get(Category, cat_id)
    if not cat:
        return None
    if "name" in data and data["name"].strip():
        cat.name = data["name"].strip()
        cat.slug = generate_slug(cat.name)
    if "is_active" in data:
        cat.is_active = bool(data["is_active"])
    if "sort_order" in data:
        cat.sort_order = int(data["sort_order"])
    return cat

def delete_admin_category(cat_id):
    cat = db.session.get(Category, cat_id)
    if cat:
        db.session.delete(cat)
    return cat


def get_admin_brands(search=""):
    stmt = select(Brand).order_by(Brand.name.asc())
    if search:
        stmt = stmt.where(Brand.name.ilike(f"%{search}%"))
    return db.session.execute(stmt).scalars().all()

def create_admin_brand(name, industry=None, is_active=True):
    slug = generate_slug(name)
    if db.session.execute(select(Brand).where(Brand.slug == slug)).scalar_one_or_none():
        raise ValueError(f"Brand with slug '{slug}' already exists")
    brand = Brand(name=name, slug=slug, industry=industry, is_active=is_active)
    db.session.add(brand)
    return brand

def update_admin_brand(brand_id, data):
    brand = db.session.get(Brand, brand_id)
    if not brand:
        return None
    if "name" in data and data["name"].strip():
        brand.name = data["name"].strip()
        brand.slug = generate_slug(brand.name)
    if "is_active" in data:
        brand.is_active = bool(data["is_active"])
    if "industry" in data:
        brand.industry = data["industry"]
    if "sort_order" in data:
        brand.sort_order = int(data["sort_order"])
    return brand

def delete_admin_brand(brand_id):
    brand = db.session.get(Brand, brand_id)
    if brand:
        db.session.delete(brand)
    return brand


def get_admin_topics(search=""):
    stmt = select(Topic).order_by(Topic.name.asc())
    if search:
        stmt = stmt.where(Topic.name.ilike(f"%{search}%"))
    return db.session.execute(stmt).scalars().all()

def create_admin_topic(name, is_active=True):
    slug = generate_slug(name)
    if db.session.execute(select(Topic).where(Topic.slug == slug)).scalar_one_or_none():
        raise ValueError(f"Topic with slug '{slug}' already exists")
    topic = Topic(name=name, slug=slug, is_active=is_active)
    db.session.add(topic)
    return topic

def update_admin_topic(topic_id, data):
    topic = db.session.get(Topic, topic_id)
    if not topic:
        return None
    if "name" in data and data["name"].strip():
        topic.name = data["name"].strip()
        topic.slug = generate_slug(topic.name)
    if "is_active" in data:
        topic.is_active = bool(data["is_active"])
    if "is_featured" in data:
        topic.is_featured = bool(data["is_featured"])
    if "sort_order" in data:
        topic.sort_order = int(data["sort_order"])
    return topic

def delete_admin_topic(topic_id):
    topic = db.session.get(Topic, topic_id)
    if topic:
        db.session.delete(topic)
    return topic


def get_admin_sections(search=""):
    stmt = select(Section).order_by(Section.name.asc())
    if search:
        stmt = stmt.where(Section.name.ilike(f"%{search}%"))
    return db.session.execute(stmt).scalars().all()

def update_admin_section(section_id, data):
    section = db.session.get(Section, section_id)
    if not section:
        return None
    if "is_active" in data:
        section.is_active = bool(data["is_active"])
    if "description" in data:
        section.description = data["description"]
    if "sort_order" in data:
        section.sort_order = int(data["sort_order"])
    return section


def get_admin_attributes(search=""):
    stmt = select(AttributeFacet).order_by(AttributeFacet.name.asc())
    if search:
        stmt = stmt.where(AttributeFacet.name.ilike(f"%{search}%"))
    return db.session.execute(stmt).scalars().all()

def create_admin_attribute(name, category_id=None):
    slug = generate_slug(name)
    if db.session.execute(select(AttributeFacet).where(AttributeFacet.slug == slug)).scalar_one_or_none():
        raise ValueError(f"Attribute with slug '{slug}' already exists")
    
    if category_id:
        if not db.session.get(Category, category_id):
            raise ValueError("Invalid category ID")
            
    attr = AttributeFacet(name=name, slug=slug, category_id=category_id)
    db.session.add(attr)
    return attr

def update_admin_attribute(attr_id, data):
    attr = db.session.get(AttributeFacet, attr_id)
    if not attr:
        return None
    if "name" in data and data["name"].strip():
        attr.name = data["name"].strip()
        attr.slug = generate_slug(attr.name)
    if "category_id" in data:
        cat_id = data["category_id"]
        if cat_id:
            if not db.session.get(Category, cat_id):
                raise ValueError("Invalid category ID")
            attr.category_id = cat_id
        else:
            attr.category_id = None
    return attr

def delete_admin_attribute(attr_id):
    attr = db.session.get(AttributeFacet, attr_id)
    if attr:
        db.session.delete(attr)
    return attr

def get_admin_taxonomy_analytics():
    total_content = db.session.scalar(select(func.count(Content.id))) or 0
    missing_category = db.session.scalar(select(func.count(Content.id)).where(Content.category_id == None)) or 0
    missing_section = db.session.scalar(select(func.count(Content.id)).where(Content.section_id == None)) or 0
    
    content_with_brands = db.session.scalar(select(func.count(func.distinct(content_brands.c.content_id)))) or 0
    missing_brand = total_content - content_with_brands

    total_entities = 0
    orphans = 0
    
    entities_config = [
        (Category, ~db.session.query(Content.id).filter(Content.category_id == Category.id).exists(), ~db.session.query(Item.id).filter(Item.category_id == Category.id).exists()),
        (Brand, ~db.session.query(content_brands.c.content_id).filter(content_brands.c.brand_id == Brand.id).exists(), ~db.session.query(Item.id).filter(Item.brand_id == Brand.id).exists()),
        (Topic, ~db.session.query(content_topics.c.content_id).filter(content_topics.c.topic_id == Topic.id).exists(), None),
        (Section, ~db.session.query(Content.id).filter(Content.section_id == Section.id).exists(), None)
    ]
    
    for model, cond1, cond2 in entities_config:
        total_entities += db.session.scalar(select(func.count(model.id))) or 0
        orphan_query = select(func.count(model.id)).where(cond1)
        if cond2 is not None:
            orphan_query = orphan_query.where(cond2)
        orphans += db.session.scalar(orphan_query) or 0

    return {
        "content_coverage": {
            "total_content": total_content,
            "missing_category": missing_category,
            "missing_section": missing_section,
            "missing_brand": missing_brand,
            "category_coverage_pct": round(((total_content - missing_category) / total_content * 100) if total_content else 0, 1),
            "section_coverage_pct": round(((total_content - missing_section) / total_content * 100) if total_content else 0, 1),
            "brand_coverage_pct": round(((content_with_brands) / total_content * 100) if total_content else 0, 1),
        },
        "health": {
            "total_entities": total_entities,
            "orphan_entities": orphans,
            "orphan_pct": round((orphans / total_entities * 100) if total_entities else 0, 1)
        }
    }

def get_admin_entity_or_404(model, entity_id):
    return db.session.get(model, entity_id)

def get_admin_taxonomy_related_metadata(entity, entity_type):
    from app.domains.relationships import content_brands, content_topics, content_items
    from app.domains.item.models import ItemVariant, ItemImage
    data = {}
    
    top_contents_query = select(Content).order_by(Content.view_count.desc()).limit(5)
    
    def _format_breakdown_and_engagement(type_breakdown, engagement):
        type_strs = [f"{count} {type_.capitalize()}{'s' if count != 1 else ''}" for type_, count in type_breakdown]
        data["content types"] = ", ".join(type_strs) if type_strs else "—"
        
        views, likes, shares = engagement if engagement else (0, 0, 0)
        data["total engagement"] = f"{int(views or 0)} views, {int(likes or 0)} likes, {int(shares or 0)} shares"
    
    if entity_type == "category":
        data["content count"] = str(db.session.scalar(select(func.count()).select_from(Content).where(Content.category_id == entity.id)) or 0)
        
        type_breakdown = db.session.execute(select(Content.object_type, func.count(Content.id)).where(Content.category_id == entity.id).group_by(Content.object_type)).all()
        engagement = db.session.execute(select(func.sum(Content.view_count), func.sum(Content.like_count), func.sum(Content.share_count)).where(Content.category_id == entity.id)).first()
        _format_breakdown_and_engagement(type_breakdown, engagement)
        
        total_items = db.session.scalar(select(func.count()).select_from(Item).where(Item.category_id == entity.id)) or 0
        data["item count"] = str(total_items)
        
        data["child categories"] = str(db.session.scalar(select(func.count()).select_from(Category).where(Category.parent_id == entity.id)) or 0)
        
        variants_count = db.session.scalar(
            select(func.count(ItemVariant.id)).join(Item, Item.id == ItemVariant.item_id).where(Item.category_id == entity.id)
        ) or 0
        data["avg variants per item"] = str(round(variants_count / total_items, 1) if total_items > 0 else 0)
        
        items_with_images = db.session.scalar(
            select(func.count(func.distinct(ItemImage.item_id))).join(Item, Item.id == ItemImage.item_id).where(Item.category_id == entity.id)
        ) or 0
        data["image coverage"] = f"{round((items_with_images / total_items) * 100)}%" if total_items > 0 else "0%"
        
        items_with_content = db.session.scalar(
            select(func.count(func.distinct(content_items.c.item_id))).join(Item, Item.id == content_items.c.item_id).where(Item.category_id == entity.id)
        ) or 0
        data["items without content"] = str(total_items - items_with_content)
        
        top_contents = db.session.execute(top_contents_query.where(Content.category_id == entity.id)).scalars().all()
        
    elif entity_type == "brand":
        data["content count"] = str(db.session.scalar(select(func.count()).select_from(content_brands).where(content_brands.c.brand_id == entity.id)) or 0)
        
        type_breakdown = db.session.execute(select(Content.object_type, func.count(Content.id)).join(content_brands, content_brands.c.content_id == Content.id).where(content_brands.c.brand_id == entity.id).group_by(Content.object_type)).all()
        engagement = db.session.execute(select(func.sum(Content.view_count), func.sum(Content.like_count), func.sum(Content.share_count)).join(content_brands, content_brands.c.content_id == Content.id).where(content_brands.c.brand_id == entity.id)).first()
        _format_breakdown_and_engagement(type_breakdown, engagement)
        
        total_items = db.session.scalar(select(func.count()).select_from(Item).where(Item.brand_id == entity.id)) or 0
        data["item count"] = str(total_items)
        
        avg_price = db.session.scalar(
            select(func.avg(ItemVariant.price)).join(Item, Item.id == ItemVariant.item_id).where(Item.brand_id == entity.id)
        )
        data["average price"] = f"${avg_price:.2f}" if avg_price else "—"
        
        items_with_images = db.session.scalar(
            select(func.count(func.distinct(ItemImage.item_id))).join(Item, Item.id == ItemImage.item_id).where(Item.brand_id == entity.id)
        ) or 0
        data["image coverage"] = f"{round((items_with_images / total_items) * 100)}%" if total_items > 0 else "0%"
        
        top_items = db.session.execute(
            select(Item).where(Item.brand_id == entity.id).order_by(Item.click_count.desc()).limit(5)
        ).scalars().all()
        data["_top_items"] = top_items
        
        top_contents = db.session.execute(top_contents_query.join(content_brands, content_brands.c.content_id == Content.id).where(content_brands.c.brand_id == entity.id)).scalars().all()
        
    elif entity_type == "topic":
        data["content count"] = str(db.session.scalar(select(func.count()).select_from(content_topics).where(content_topics.c.topic_id == entity.id)) or 0)
        
        type_breakdown = db.session.execute(select(Content.object_type, func.count(Content.id)).join(content_topics, content_topics.c.content_id == Content.id).where(content_topics.c.topic_id == entity.id).group_by(Content.object_type)).all()
        engagement = db.session.execute(select(func.sum(Content.view_count), func.sum(Content.like_count), func.sum(Content.share_count)).join(content_topics, content_topics.c.content_id == Content.id).where(content_topics.c.topic_id == entity.id)).first()
        _format_breakdown_and_engagement(type_breakdown, engagement)
        
        rel_cats = db.session.scalar(
            select(func.count(func.distinct(Content.category_id)))
            .join(content_topics, content_topics.c.content_id == Content.id)
            .filter(content_topics.c.topic_id == entity.id)
        ) or 0
        data["related categories"] = str(rel_cats)
        
        rel_brands = db.session.scalar(
            select(func.count(func.distinct(content_brands.c.brand_id)))
            .join(content_topics, content_topics.c.content_id == content_brands.c.content_id)
            .filter(content_topics.c.topic_id == entity.id)
        ) or 0
        data["related brands"] = str(rel_brands)
        top_contents = db.session.execute(top_contents_query.join(content_topics, content_topics.c.content_id == Content.id).where(content_topics.c.topic_id == entity.id)).scalars().all()
        
    elif entity_type == "section":
        data["content count"] = str(db.session.scalar(select(func.count()).select_from(Content).where(Content.section_id == entity.id)) or 0)
        
        type_breakdown = db.session.execute(select(Content.object_type, func.count(Content.id)).where(Content.section_id == entity.id).group_by(Content.object_type)).all()
        engagement = db.session.execute(select(func.sum(Content.view_count), func.sum(Content.like_count), func.sum(Content.share_count)).where(Content.section_id == entity.id)).first()
        _format_breakdown_and_engagement(type_breakdown, engagement)
        
        cat_count = db.session.scalar(
            select(func.count(func.distinct(Content.category_id)))
            .filter(Content.section_id == entity.id)
        ) or 0
        data["category count"] = str(cat_count)
        
        rel_brands = db.session.scalar(
            select(func.count(func.distinct(content_brands.c.brand_id)))
            .join(Content, Content.id == content_brands.c.content_id)
            .filter(Content.section_id == entity.id)
        ) or 0
        data["related brands"] = str(rel_brands)
        top_contents = db.session.execute(top_contents_query.where(Content.section_id == entity.id)).scalars().all()
        
    elif entity_type == "attribute":
        data["content count"] = str(db.session.scalar(select(func.count()).select_from(content_attributes).where(content_attributes.c.attribute_id == entity.id)) or 0)
        
        type_breakdown = db.session.execute(select(Content.object_type, func.count(Content.id)).join(content_attributes, content_attributes.c.content_id == Content.id).where(content_attributes.c.attribute_id == entity.id).group_by(Content.object_type)).all()
        engagement = db.session.execute(select(func.sum(Content.view_count), func.sum(Content.like_count), func.sum(Content.share_count)).join(content_attributes, content_attributes.c.content_id == Content.id).where(content_attributes.c.attribute_id == entity.id)).first()
        _format_breakdown_and_engagement(type_breakdown, engagement)
        
        top_contents = db.session.execute(top_contents_query.join(content_attributes, content_attributes.c.content_id == Content.id).where(content_attributes.c.attribute_id == entity.id)).scalars().all()

    elif entity_type in ["gender_facet", "intent_facet", "price_tier_facet"]:
        field_mapping = {
            "gender_facet": Content.gender_id,
            "intent_facet": Content.intent_id,
            "price_tier_facet": Content.price_tier_id
        }
        field = field_mapping[entity_type]
        
        data["content count"] = str(db.session.scalar(select(func.count()).select_from(Content).where(field == entity.id)) or 0)
        
        type_breakdown = db.session.execute(select(Content.object_type, func.count(Content.id)).where(field == entity.id).group_by(Content.object_type)).all()
        engagement = db.session.execute(select(func.sum(Content.view_count), func.sum(Content.like_count), func.sum(Content.share_count)).where(field == entity.id)).first()
        _format_breakdown_and_engagement(type_breakdown, engagement)
        
        top_contents = db.session.execute(top_contents_query.where(field == entity.id)).scalars().all()

    data["_top_contents"] = top_contents
    return data

def get_admin_source_metadata(source):
    from app.domains.content.models import Article
    
    article_count = db.session.scalar(
        select(func.count()).select_from(Content).where(Content.source_id == source.id)
    ) or 0
    
    analytics = db.session.query(
        func.avg(Article.quality_score),
        func.avg(Article.word_count),
        func.count(Article.id).filter(Article.is_content_scraped == True),
        func.min(Content.published_at),
        func.max(Content.published_at)
    ).select_from(Content).join(Article, Content.object_id == Article.id).filter(Content.source_id == source.id, Content.object_type == 'article').first()
    
    avg_quality = round(analytics[0], 1) if analytics and analytics[0] else 0
    avg_words = int(analytics[1]) if analytics and analytics[1] else 0
    scraped_count = analytics[2] if analytics and analytics[2] else 0
    scrape_cov = round((scraped_count / article_count * 100), 1) if article_count > 0 else 0
    date_min = analytics[3].strftime('%Y-%m-%d') if analytics and analytics[3] else "—"
    date_max = analytics[4].strftime('%Y-%m-%d') if analytics and analytics[4] else "—"
    
    return {
        "id": f"#{source.id}",
        "name": source.name,
        "slug": source.slug,
        "domain": source.domain,
        "authority score": str(source.authority_score),
        "status": source.is_active,
        "avg quality score": str(avg_quality),
        "avg word count": str(avg_words),
        "scrape coverage": f"{scrape_cov}%",
        "published date range": f"{date_min} to {date_max}",
        "article count": str(article_count)
    }

def get_admin_source_inspect_raw(id):
    from app.domains.taxonomy.models import Source
    source = db.session.get(Source, id)
    if not source:
        return None
        
    content_count = db.session.scalar(select(func.count(Content.id)).filter(Content.source_id == id)) or 0
    
    from app.domains.content.models import Article
    analytics = db.session.query(
        func.avg(Article.quality_score),
        func.avg(Article.word_count),
        func.count(Article.id).filter(Article.is_content_scraped == True),
        func.min(Content.published_at),
        func.max(Content.published_at)
    ).select_from(Content).join(Article, Content.object_id == Article.id).filter(Content.source_id == id, Content.object_type == 'article').first()
    
    type_counts = db.session.execute(
        select(Content.object_type, func.count(Content.id))
        .where(Content.source_id == id)
        .group_by(Content.object_type)
    ).all()
    
    channel_counts = db.session.execute(
        select(Content.ingestion_origin, func.count(Content.id))
        .where(Content.source_id == id)
        .where(Content.ingestion_origin.is_not(None))
        .group_by(Content.ingestion_origin)
    ).all()
    
    category_counts = db.session.scalar(
        select(func.count(func.distinct(Content.category_id)))
        .where(Content.source_id == id)
    ) or 0
    
    status_counts = db.session.execute(
        select(Article.status, func.count(Article.id))
        .join(Content, Content.object_id == Article.id)
        .where(Content.source_id == id)
        .where(Content.object_type == 'article')
        .group_by(Article.status)
    ).all()
    
    eng_stats = db.session.execute(
        select(
            func.sum(Content.view_count).label("views"),
            func.sum(Content.like_count).label("likes"),
            func.sum(Content.save_count).label("saves"),
            func.sum(Content.comment_count).label("comments")
        ).where(Content.source_id == id)
    ).first()
    
    fetch_health = db.session.execute(
        select(
            func.sum(LastAPIFetch.success_count).label("success"),
            func.sum(LastAPIFetch.failure_count).label("failures"),
            func.max(LastAPIFetch.consecutive_failures).label("consecutive"),
            func.max(LastAPIFetch.last_fetched_at).label("last_fetch")
        )
        .where(func.lower(LastAPIFetch.source) == source.slug.lower())
    ).first()
    
    primary_count = db.session.scalar(
        select(func.count(Article.id))
        .where(Article.primary_source_id != None)
        .join(ArticleSource, Article.primary_source_id == ArticleSource.id)
        .where(ArticleSource.source_id == id)
    ) or 0
    
    secondary_count = db.session.scalar(
        select(func.count(ArticleSource.id))
        .where(ArticleSource.source_id == id)
    ) or 0
    
    top_articles = db.session.execute(
        select(Content.id, Content.title, Content.view_count)
        .where(Content.source_id == id)
        .where(Content.object_type == 'article')
        .order_by(Content.view_count.desc())
        .limit(5)
    ).all()
    
    return (
        source, content_count, analytics, type_counts, channel_counts,
        category_counts, status_counts, eng_stats, fetch_health,
        primary_count, secondary_count, top_articles
    )
