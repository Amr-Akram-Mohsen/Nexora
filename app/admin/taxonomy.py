# app/admin/taxonomy.py
from flask import Blueprint, jsonify, request, render_template
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.taxonomy.models import Category, Brand, Topic, Section, Source
from app.shared.utils.slug import generate_slug
from app.admin.helpers import parse_pagination_params, make_rows_response
from sqlalchemy import select, func
from app.domains.content.models import Content
from app.domains.item.models import Item

bp = Blueprint("api_taxonomy", __name__, url_prefix="/admin/taxonomy")


@bp.before_request
@admin_required
def require_admin():
    """Ensure all taxonomy management endpoints require admin privilege."""
    pass


# ─────────────────────────────────────────────
# CATEGORIES
# ─────────────────────────────────────────────

@bp.route("/categories", methods=["GET"])
def list_categories():
    search = request.args.get("search", "").strip()
    stmt = select(Category).order_by(Category.name.asc())
    if search:
        stmt = stmt.where(Category.name.ilike(f"%{search}%"))
    cats = db.session.execute(stmt).scalars().all()
    return jsonify([_serialize_category(c) for c in cats])


@bp.route("/categories", methods=["POST"])
@admin_required
def create_category():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    slug = generate_slug(name)
    if db.session.execute(select(Category).where(Category.slug == slug)).scalar_one_or_none():
        return jsonify({"error": f"Category with slug '{slug}' already exists"}), 409
    cat = Category(name=name, slug=slug, is_active=data.get("is_active", True))
    db.session.add(cat)
    db.session.commit()
    return jsonify(_serialize_category(cat)), 201


@bp.route("/categories/<int:id>", methods=["PATCH"])
@admin_required
def update_category(id):
    cat = db.session.get(Category, id)
    if not cat:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json() or {}
    if "name" in data and data["name"].strip():
        cat.name = data["name"].strip()
        cat.slug = generate_slug(cat.name)
    if "is_active" in data:
        cat.is_active = bool(data["is_active"])
    if "sort_order" in data:
        cat.sort_order = int(data["sort_order"])
    db.session.commit()
    return jsonify(_serialize_category(cat))


@bp.route("/categories/<int:id>", methods=["DELETE"])
@admin_required
def delete_category(id):
    cat = db.session.get(Category, id)
    if not cat:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(cat)
    db.session.commit()
    return jsonify({"success": True, "message": f"Category '{cat.name}' deleted."})

def _serialize_taxonomy(t):
    data = {
        "id": t.id,
        "name": t.name,
        "status": 'active' if t.is_active else 'inactive',
    }
    if isinstance(t, Category):
        data["type"] = "Leaf" if t.is_leaf else "Parent"
    if isinstance(t, Section):
        data['description'] = t.description
    if isinstance(t, (Brand, Topic)):
        data['featured'] = "Featured" if t.is_featured else "Not Featured"
    return data

def _serialize_category(c):
    return {
        "id": c.id,
        "name": c.name,
        "slug": c.slug,
        "is_active": c.is_active,
        "is_leaf": c.is_leaf,
        "sort_order": c.sort_order,
        "parent_id": c.parent_id,
    }


# ─────────────────────────────────────────────
# BRANDS
# ─────────────────────────────────────────────

@bp.route("/brands", methods=["GET"])
def list_brands():
    search = request.args.get("search", "").strip()
    stmt = select(Brand).order_by(Brand.name.asc())
    if search:
        stmt = stmt.where(Brand.name.ilike(f"%{search}%"))
    brands = db.session.execute(stmt).scalars().all()
    return jsonify([_serialize_brand(b) for b in brands])


@bp.route("/brands", methods=["POST"])
@admin_required
def create_brand():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    slug = generate_slug(name)
    if db.session.execute(select(Brand).where(Brand.slug == slug)).scalar_one_or_none():
        return jsonify({"error": f"Brand with slug '{slug}' already exists"}), 409
    brand = Brand(
        name=name,
        slug=slug,
        industry=data.get("industry"),
        is_active=data.get("is_active", True),
    )
    db.session.add(brand)
    db.session.commit()
    return jsonify(_serialize_brand(brand)), 201


@bp.route("/brands/<int:id>", methods=["PATCH"])
@admin_required
def update_brand(id):
    brand = db.session.get(Brand, id)
    if not brand:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json() or {}
    if "name" in data and data["name"].strip():
        brand.name = data["name"].strip()
        brand.slug = generate_slug(brand.name)
    if "is_active" in data:
        brand.is_active = bool(data["is_active"])
    if "industry" in data:
        brand.industry = data["industry"]
    if "sort_order" in data:
        brand.sort_order = int(data["sort_order"])
    db.session.commit()
    return jsonify(_serialize_brand(brand))


@bp.route("/brands/<int:id>", methods=["DELETE"])
@admin_required
def delete_brand(id):
    brand = db.session.get(Brand, id)
    if not brand:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(brand)
    db.session.commit()
    return jsonify({"success": True, "message": f"Brand '{brand.name}' deleted."})


def _serialize_brand(b):
    return {
        "id": b.id,
        "name": b.name,
        "slug": b.slug,
        "industry": b.industry,
        "is_active": b.is_active,
        "is_featured": b.is_featured,
        "sort_order": b.sort_order,
    }


# ─────────────────────────────────────────────
# TOPICS
# ─────────────────────────────────────────────

@bp.route("/topics", methods=["GET"])
def list_topics():
    search = request.args.get("search", "").strip()
    stmt = select(Topic).order_by(Topic.name.asc())
    if search:
        stmt = stmt.where(Topic.name.ilike(f"%{search}%"))
    topics = db.session.execute(stmt).scalars().all()
    return jsonify([_serialize_topic(t) for t in topics])


@bp.route("/topics", methods=["POST"])
@admin_required
def create_topic():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    slug = generate_slug(name)
    if db.session.execute(select(Topic).where(Topic.slug == slug)).scalar_one_or_none():
        return jsonify({"error": f"Topic with slug '{slug}' already exists"}), 409
    topic = Topic(name=name, slug=slug, is_active=data.get("is_active", True))
    db.session.add(topic)
    db.session.commit()
    return jsonify(_serialize_topic(topic)), 201


@bp.route("/topics/<int:id>", methods=["PATCH"])
@admin_required
def update_topic(id):
    topic = db.session.get(Topic, id)
    if not topic:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json() or {}
    if "name" in data and data["name"].strip():
        topic.name = data["name"].strip()
        topic.slug = generate_slug(topic.name)
    if "is_active" in data:
        topic.is_active = bool(data["is_active"])
    if "is_featured" in data:
        topic.is_featured = bool(data["is_featured"])
    if "sort_order" in data:
        topic.sort_order = int(data["sort_order"])
    db.session.commit()
    return jsonify(_serialize_topic(topic))


@bp.route("/topics/<int:id>", methods=["DELETE"])
@admin_required
def delete_topic(id):
    topic = db.session.get(Topic, id)
    if not topic:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(topic)
    db.session.commit()
    return jsonify({"success": True, "message": f"Topic '{topic.name}' deleted."})


def _serialize_topic(t):
    return {
        "id": t.id,
        "name": t.name,
        "slug": t.slug,
        "is_active": t.is_active,
        "is_featured": t.is_featured,
        "sort_order": t.sort_order,
    }


# ─────────────────────────────────────────────
# SECTIONS
# ─────────────────────────────────────────────

@bp.route("/sections", methods=["GET"])
def list_sections():
    search = request.args.get("search", "").strip()
    stmt = select(Section).order_by(Section.name.asc())
    if search:
        stmt = stmt.where(Section.name.ilike(f"%{search}%"))
    sections = db.session.execute(stmt).scalars().all()
    return jsonify([_serialize_section(s) for s in sections])


@bp.route("/sections/<int:id>", methods=["PATCH"])
@admin_required
def update_section(id):
    section = db.session.get(Section, id)
    if not section:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json() or {}
    if "is_active" in data:
        section.is_active = bool(data["is_active"])
    if "description" in data:
        section.description = data["description"]
    if "sort_order" in data:
        section.sort_order = int(data["sort_order"])
    db.session.commit()
    return jsonify(_serialize_section(section))


def _serialize_section(s):
    return {
        "id": s.id,
        "name": s.name,
        "slug": s.slug,
        "description": s.description,
        "is_active": s.is_active,
        "sort_order": s.sort_order,
    }


# ─────────────────────────────────────────────
# HTML PARTIAL ROWS ENDPOINTS
# ─────────────────────────────────────────────

@bp.route("/categories/rows", methods=["GET"])
def categories_rows():
    """Return server-rendered HTML rows partial for categories AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=50)
    search = request.args.get("search", "").strip()

    stmt = select(Category).order_by(Category.name.asc())
    if search:
        stmt = stmt.where(Category.name.ilike(f"%{search}%"))
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    serialized = [_serialize_taxonomy(c) for c in pagination.items]

    html = render_template("admin/components/_rows.html", items=serialized, domain_type='category')
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )


@bp.route("/brands/rows", methods=["GET"])
def brands_rows():
    """Return server-rendered HTML rows partial for brands AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=50)
    search = request.args.get("search", "").strip()

    stmt = select(Brand).order_by(Brand.name.asc())
    if search:
        stmt = stmt.where(Brand.name.ilike(f"%{search}%"))
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    serialized = [_serialize_taxonomy(b) for b in pagination.items]

    html = render_template("admin/components/_rows.html", items=serialized, domain_type='brand')
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )


@bp.route("/topics/rows", methods=["GET"])
def topics_rows():
    """Return server-rendered HTML rows partial for topics AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=50)
    search = request.args.get("search", "").strip()

    stmt = select(Topic).order_by(Topic.name.asc())
    if search:
        stmt = stmt.where(Topic.name.ilike(f"%{search}%"))
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    serialized = [_serialize_taxonomy(t) for t in pagination.items]

    html = render_template("admin/components/_rows.html", items=serialized, domain_type='topic')
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )


@bp.route("/sections/rows", methods=["GET"])
def sections_rows():
    """Return server-rendered HTML rows partial for sections AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=50)
    search = request.args.get("search", "").strip()

    stmt = select(Section).order_by(Section.name.asc())
    if search:
        stmt = stmt.where(Section.name.ilike(f"%{search}%"))
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    serialized = [_serialize_taxonomy(s) for s in pagination.items]

    html = render_template("admin/components/_rows.html", items=serialized, domain_type='section')
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )

# ─────────────────────────────────────────────
# INSPECT HELPERS & ENDPOINTS
# ─────────────────────────────────────────────

def _get_entity_or_404(model, id, entity_name):
    entity = db.session.get(model, id)
    if not entity:
        return None, f"<p class='text-muted'>{entity_name} not found.</p>"
    return entity, None

def _get_taxonomy_related_metadata(entity, entity_type):
    from app.domains.relationships import content_brands, content_topics, content_items
    from app.domains.item.models import ItemVariant, ItemImage
    data = {}
    
    top_contents_query = select(Content).order_by(Content.view_count.desc()).limit(5)
    
    if entity_type == "category":
        data["content count"] = str(db.session.scalar(select(func.count()).select_from(Content).where(Content.category_id == entity.id)) or 0)
        
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
        if top_items:
            data["top clicked items"] = {"value": render_template("admin/components/_top_items_table.html", items=top_items), "is_custom": True}
        
        top_contents = db.session.execute(top_contents_query.join(content_brands, content_brands.c.content_id == Content.id).where(content_brands.c.brand_id == entity.id)).scalars().all()
        
    elif entity_type == "topic":
        data["content count"] = str(db.session.scalar(select(func.count()).select_from(content_topics).where(content_topics.c.topic_id == entity.id)) or 0)
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
        
    data["top content"] = {"value": render_template("admin/components/content/_top_content_table.html", contents=top_contents), "is_custom": True}
    return data

def _get_taxonomy_inspect_table(entity, entity_type, metadata):
    from app.admin.helpers import format_status, format_featured
    from app.admin.tables import get_inspect_table
    
    data = {
        "id": f"#{entity.id}",
        "name": entity.name,
        "status": format_status(entity.is_active),
        "sort order": str(entity.sort_order) if hasattr(entity, "sort_order") else "0",
    }
    data.update(metadata)
    
    if entity_type == "category":
        data["slug"] = entity.slug
        data["heirarchy level"] = "Leaf" if entity.is_leaf else "Parent"
        if entity.is_leaf and entity.parent:
            data["parent name"] = entity.parent.name
        return get_inspect_table("categories", data)
    elif entity_type == "brand":
        data["slug"] = entity.slug
        data["industry"] = entity.industry or "—"
        data["featured"] = format_featured(entity.is_featured)
        return get_inspect_table("brands", data)
    elif entity_type == "topic":
        data["slug"] = entity.slug
        data["featured"] = format_featured(entity.is_featured)
        return get_inspect_table("topics", data)
    elif entity_type == "section":
        import json
        data["slug"] = entity.slug
        data["description"] = entity.description or "—"
        data["allowed filters"] = json.dumps(entity.allowed_filters) if entity.allowed_filters else "—"
        return get_inspect_table("sections", data)

@bp.route("/categories/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_category(id):
    cat, err = _get_entity_or_404(Category, id, "Category")
    if err: return err, 404
    metadata = _get_taxonomy_related_metadata(cat, "category")
    inspect_table = _get_taxonomy_inspect_table(cat, "category", metadata)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table)

@bp.route("/brands/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_brand(id):
    brand, err = _get_entity_or_404(Brand, id, "Brand")
    if err: return err, 404
    metadata = _get_taxonomy_related_metadata(brand, "brand")
    inspect_table = _get_taxonomy_inspect_table(brand, "brand", metadata)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table)

@bp.route("/topics/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_topic(id):
    topic, err = _get_entity_or_404(Topic, id, "Topic")
    if err: return err, 404
    metadata = _get_taxonomy_related_metadata(topic, "topic")
    inspect_table = _get_taxonomy_inspect_table(topic, "topic", metadata)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table)

@bp.route("/sections/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_section(id):
    section, err = _get_entity_or_404(Section, id, "Section")
    if err: return err, 404
    metadata = _get_taxonomy_related_metadata(section, "section")
    inspect_table = _get_taxonomy_inspect_table(section, "section", metadata)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table)

@bp.route("/sources/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_source(id):
    source, err = _get_entity_or_404(Source, id, "Source")
    if err: return err, 404
    from app.admin.helpers import format_status
    from app.admin.tables import get_inspect_table
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
    
    data = {
        "id": f"#{source.id}",
        "name": source.name,
        "slug": source.slug,
        "domain": source.domain,
        "authority score": str(source.authority_score),
        "status": format_status(source.is_active),
        "avg quality score": str(avg_quality),
        "avg word count": str(avg_words),
        "scrape coverage": f"{scrape_cov}%",
        "published date range": f"{date_min} to {date_max}",
        "article count": str(article_count)
    }
    
    inspect_table = get_inspect_table("sources", data)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table)
