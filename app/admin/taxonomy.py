# app/admin/taxonomy.py
from flask import Blueprint, jsonify, request, render_template
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.taxonomy.models import Category, Brand, Topic, Section, Source, AttributeFacet, GenderFacet, IntentFacet, PriceTierFacet
from app.shared.utils.slug import generate_slug
from app.admin.helpers import parse_pagination_params, make_rows_response
from sqlalchemy import select, func, update
import difflib
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

def _serialize_taxonomy(t, counts=None, health=None):
    data = {
        "id": t.id,
        "name": t.name,
        "status": 'active' if t.is_active else 'inactive',
    }
    if isinstance(t, Category):
        data["type"] = "Leaf" if t.is_leaf else "Parent"
    if isinstance(t, Section):
        data['description'] = t.description
        data['filter config'] = "Configured" if t.allowed_filters else "Not Configured"
    if isinstance(t, Brand):
        data['industry'] = t.industry or "—"
    if isinstance(t, (Brand, Topic)):
        data['featured'] = "Featured" if t.is_featured else "Not Featured"
        
    if counts:
        for k, v in counts.items():
            data[k] = str(v)
            
    if health:
        data["health"] = health
        
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
    status = request.args.get("status")
    health = request.args.get("health")

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
        
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    
    item_ids = [c.id for c in pagination.items]
    content_counts = {}
    item_counts = {}
    children_counts = {}
    
    if item_ids:
        content_counts = dict(db.session.execute(select(Content.category_id, func.count(Content.id)).where(Content.category_id.in_(item_ids)).group_by(Content.category_id)).all())
        item_counts = dict(db.session.execute(select(Item.category_id, func.count(Item.id)).where(Item.category_id.in_(item_ids)).group_by(Item.category_id)).all())
        children_counts = dict(db.session.execute(select(Category.parent_id, func.count(Category.id)).where(Category.parent_id.in_(item_ids)).group_by(Category.parent_id)).all())
        
    serialized = []
    for c in pagination.items:
        c_count = content_counts.get(c.id, 0)
        i_count = item_counts.get(c.id, 0)
        child_count = children_counts.get(c.id, 0)
        
        health = "ok"
        if c_count == 0 and i_count == 0:
            health = "unused"
        elif not c.is_active and (c_count > 0 or i_count > 0):
            health = "inactive-linked"
            
        counts = {
            "content count": c_count,
            "item count": i_count,
            "children count": child_count
        }
        serialized.append(_serialize_taxonomy(c, counts=counts, health=health))

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
    from app.domains.relationships import content_brands
    page, per_page = parse_pagination_params(default_per_page=50)
    search = request.args.get("search", "").strip()
    status = request.args.get("status")
    health = request.args.get("health")

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
        
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    
    item_ids = [b.id for b in pagination.items]
    content_counts = {}
    item_counts = {}
    
    if item_ids:
        from app.domains.relationships import content_brands
        content_counts = dict(db.session.execute(select(content_brands.c.brand_id, func.count(content_brands.c.content_id)).where(content_brands.c.brand_id.in_(item_ids)).group_by(content_brands.c.brand_id)).all())
        item_counts = dict(db.session.execute(select(Item.brand_id, func.count(Item.id)).where(Item.brand_id.in_(item_ids)).group_by(Item.brand_id)).all())
        
    serialized = []
    for b in pagination.items:
        c_count = content_counts.get(b.id, 0)
        i_count = item_counts.get(b.id, 0)
        
        health = "ok"
        if c_count == 0 and i_count == 0:
            health = "unused"
        elif not b.is_active and (c_count > 0 or i_count > 0):
            health = "inactive-linked"
            
        counts = {
            "content count": c_count,
            "item count": i_count,
        }
        serialized.append(_serialize_taxonomy(b, counts=counts, health=health))

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
    from app.domains.relationships import content_topics
    page, per_page = parse_pagination_params(default_per_page=50)
    search = request.args.get("search", "").strip()
    status = request.args.get("status")
    health = request.args.get("health")

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
        
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    
    item_ids = [t.id for t in pagination.items]
    content_counts = {}
    category_spread = {}
    
    if item_ids:
        from app.domains.relationships import content_topics
        content_counts = dict(db.session.execute(select(content_topics.c.topic_id, func.count(content_topics.c.content_id)).where(content_topics.c.topic_id.in_(item_ids)).group_by(content_topics.c.topic_id)).all())
        
        cat_spread_query = select(content_topics.c.topic_id, func.count(func.distinct(Content.category_id))).join(Content, Content.id == content_topics.c.content_id).where(content_topics.c.topic_id.in_(item_ids)).group_by(content_topics.c.topic_id)
        category_spread = dict(db.session.execute(cat_spread_query).all())
        
    serialized = []
    for t in pagination.items:
        c_count = content_counts.get(t.id, 0)
        cat_count = category_spread.get(t.id, 0)
        
        health = "ok"
        if c_count == 0:
            health = "unused"
        elif not t.is_active and c_count > 0:
            health = "inactive-linked"
            
        counts = {
            "content count": c_count,
            "category spread": cat_count
        }
        serialized.append(_serialize_taxonomy(t, counts=counts, health=health))

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
    status = request.args.get("status")
    health = request.args.get("health")

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
        
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    
    item_ids = [s.id for s in pagination.items]
    content_counts = {}
    category_spread = {}
    
    if item_ids:
        content_counts = dict(db.session.execute(select(Content.section_id, func.count(Content.id)).where(Content.section_id.in_(item_ids)).group_by(Content.section_id)).all())
        cat_spread_query = select(Content.section_id, func.count(func.distinct(Content.category_id))).where(Content.section_id.in_(item_ids)).group_by(Content.section_id)
        category_spread = dict(db.session.execute(cat_spread_query).all())
        
    serialized = []
    for s in pagination.items:
        c_count = content_counts.get(s.id, 0)
        cat_count = category_spread.get(s.id, 0)
        
        health = "ok"
        if c_count == 0:
            health = "unused"
        elif not s.is_active and c_count > 0:
            health = "inactive-linked"
            
        counts = {
            "content count": c_count,
            "category count": cat_count
        }
        serialized.append(_serialize_taxonomy(s, counts=counts, health=health))

    html = render_template("admin/components/_rows.html", items=serialized, domain_type='section')
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )

# ─────────────────────────────────────────────
# ATTRIBUTES
# ─────────────────────────────────────────────

@bp.route("/attributes", methods=["GET"])
def list_attributes():
    search = request.args.get("search", "").strip()
    stmt = select(AttributeFacet).order_by(AttributeFacet.name.asc())
    if search:
        stmt = stmt.where(AttributeFacet.name.ilike(f"%{search}%"))
    attrs = db.session.execute(stmt).scalars().all()
    return jsonify([_serialize_attribute(a) for a in attrs])

@bp.route("/attributes", methods=["POST"])
@admin_required
def create_attribute():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    slug = generate_slug(name)
    if db.session.execute(select(AttributeFacet).where(AttributeFacet.slug == slug)).scalar_one_or_none():
        return jsonify({"error": f"Attribute with slug '{slug}' already exists"}), 409
    
    category_id = data.get("category_id")
    if category_id:
        if not db.session.get(Category, category_id):
            return jsonify({"error": "Invalid category ID"}), 400
            
    attr = AttributeFacet(name=name, slug=slug, category_id=category_id)
    db.session.add(attr)
    db.session.commit()
    return jsonify(_serialize_attribute(attr)), 201

@bp.route("/attributes/<int:id>", methods=["PATCH"])
@admin_required
def update_attribute(id):
    attr = db.session.get(AttributeFacet, id)
    if not attr:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json() or {}
    if "name" in data and data["name"].strip():
        attr.name = data["name"].strip()
        attr.slug = generate_slug(attr.name)
    if "category_id" in data:
        cat_id = data["category_id"]
        if cat_id:
            if not db.session.get(Category, cat_id):
                return jsonify({"error": "Invalid category ID"}), 400
            attr.category_id = cat_id
        else:
            attr.category_id = None
            
    db.session.commit()
    return jsonify(_serialize_attribute(attr))

@bp.route("/attributes/<int:id>", methods=["DELETE"])
@admin_required
def delete_attribute(id):
    attr = db.session.get(AttributeFacet, id)
    if not attr:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(attr)
    db.session.commit()
    return jsonify({"success": True, "message": f"Attribute '{attr.name}' deleted."})

def _serialize_attribute(a):
    return {
        "id": a.id,
        "name": a.name,
        "slug": a.slug,
        "category_id": a.category_id,
        "category_name": a.category.name if a.category else "Global",
    }

@bp.route("/attributes/rows", methods=["GET"])
def attributes_rows():
    from app.domains.relationships import content_attributes
    page, per_page = parse_pagination_params(default_per_page=50)
    search = request.args.get("search", "").strip()
    health = request.args.get("health")

    stmt = select(AttributeFacet).order_by(AttributeFacet.name.asc())
    if search:
        stmt = stmt.where(AttributeFacet.name.ilike(f"%{search}%"))
        
    if health == "unused":
        stmt = stmt.where(
            ~db.session.query(content_attributes.c.content_id).filter(content_attributes.c.attribute_id == AttributeFacet.id).exists()
        )
        
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    
    item_ids = [a.id for a in pagination.items]
    content_counts = {}
    
    if item_ids:
        from app.domains.relationships import content_attributes
        content_counts = dict(db.session.execute(select(content_attributes.c.attribute_id, func.count(content_attributes.c.content_id)).where(content_attributes.c.attribute_id.in_(item_ids)).group_by(content_attributes.c.attribute_id)).all())
        
    serialized = []
    for a in pagination.items:
        c_count = content_counts.get(a.id, 0)
        
        health = "ok"
        if c_count == 0:
            health = "unused"
            
        data = {
            "id": a.id,
            "name": a.name,
            "category": a.category.name if a.category else "Global",
            "content count": str(c_count),
            "health": health
        }
        serialized.append(data)

    html = render_template("admin/components/_rows.html", items=serialized, domain_type='attribute')
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )

# ─────────────────────────────────────────────
# CONTENT FACETS (READ-ONLY)
# ─────────────────────────────────────────────

def _get_facet_rows(model_class, domain_type, field_name):
    page, per_page = parse_pagination_params(default_per_page=50)
    search = request.args.get("search", "").strip()
    health = request.args.get("health")

    stmt = select(model_class).order_by(model_class.name.asc())
    if search:
        stmt = stmt.where(model_class.name.ilike(f"%{search}%"))
    
    if health == "unused":
        field = getattr(Content, field_name)
        stmt = stmt.where(~db.session.query(Content.id).filter(field == model_class.id).exists())

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    
    item_ids = [f.id for f in pagination.items]
    content_counts = {}
    
    if item_ids:
        field = getattr(Content, field_name)
        content_counts = dict(db.session.execute(select(field, func.count(Content.id)).where(field.in_(item_ids)).group_by(field)).all())
        
    serialized = []
    for f in pagination.items:
        c_count = content_counts.get(f.id, 0)
        
        health = "ok"
        if c_count == 0:
            health = "unused"
            
        data = {
            "id": f.id,
            "name": f.name,
            "content count": str(c_count),
            "health": health
        }
        serialized.append(data)

    html = render_template("admin/components/_rows.html", items=serialized, domain_type=domain_type)
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )

# ─────────────────────────────────────────────
# DUPLICATES DETECTION & MERGING
# ─────────────────────────────────────────────

@bp.route("/duplicates", methods=["GET"])
def taxonomy_duplicates():
    domain = request.args.get("type")
    
    domain_map = {
        "categories": Category,
        "brands": Brand,
        "topics": Topic,
        "sections": Section,
        "attributes": AttributeFacet,
    }
    
    if domain not in domain_map:
        return jsonify({"error": "Invalid domain"}), 400
        
    model_class = domain_map[domain]
    
    # Fetch all records
    records = db.session.execute(select(model_class)).scalars().all()
    
    # O(N^2) similarity search (fine for <10k rows)
    duplicates = []
    
    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            r1 = records[i]
            r2 = records[j]
            
            # Simple normalization similarity
            s1 = r1.name.lower().strip()
            s2 = r2.name.lower().strip()
            
            if s1 == s2:
                similarity = 100
            else:
                similarity = int(difflib.SequenceMatcher(None, s1, s2).ratio() * 100)
                
            if similarity > 85:  # threshold
                duplicates.append({
                    "source": {"id": r2.id, "name": r2.name},
                    "target": {"id": r1.id, "name": r1.name},
                    "similarity": similarity
                })
                
    # Sort by similarity descending
    duplicates.sort(key=lambda x: x["similarity"], reverse=True)
    return jsonify(duplicates[:50])

@bp.route("/merge", methods=["POST"])
@admin_required
def taxonomy_merge():
    data = request.json or {}
    domain = data.get("domain")
    source_id = data.get("source_id")
    target_id = data.get("target_id")
    
    if not domain or not source_id or not target_id:
        return jsonify({"error": "Missing parameters"}), 400
        
    domain_map = {
        "categories": Category,
        "brands": Brand,
        "topics": Topic,
        "sections": Section,
        "attributes": AttributeFacet,
    }
    
    if domain not in domain_map:
        return jsonify({"error": "Invalid domain"}), 400
        
    model_class = domain_map[domain]
    
    source = db.session.get(model_class, source_id)
    target = db.session.get(model_class, target_id)
    
    if not source or not target:
        return jsonify({"error": "Entities not found"}), 404
        
    try:
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
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────────
# ANALYTICS DASHBOARD
# ─────────────────────────────────────────────

@bp.route("/analytics", methods=["GET"])
def taxonomy_analytics():
    total_content = db.session.scalar(select(func.count(Content.id))) or 0
    
    missing_category = db.session.scalar(select(func.count(Content.id)).where(Content.category_id == None)) or 0
    missing_section = db.session.scalar(select(func.count(Content.id)).where(Content.section_id == None)) or 0
    
    from app.domains.relationships import content_brands
    content_with_brands = db.session.scalar(select(func.count(func.distinct(content_brands.c.content_id)))) or 0
    missing_brand = total_content - content_with_brands

    total_entities = 0
    orphans = 0
    
    # Quick count of unused entities using NOT EXISTS
    # Categories
    total_entities += db.session.scalar(select(func.count(Category.id))) or 0
    orphans += db.session.scalar(
        select(func.count(Category.id)).where(
            ~db.session.query(Content.id).filter(Content.category_id == Category.id).exists()
        ).where(
            ~db.session.query(Item.id).filter(Item.category_id == Category.id).exists()
        )
    ) or 0
    
    # Brands
    total_entities += db.session.scalar(select(func.count(Brand.id))) or 0
    orphans += db.session.scalar(
        select(func.count(Brand.id)).where(
            ~db.session.query(content_brands.c.content_id).filter(content_brands.c.brand_id == Brand.id).exists()
        ).where(
            ~db.session.query(Item.id).filter(Item.brand_id == Brand.id).exists()
        )
    ) or 0
    
    # Topics
    from app.domains.relationships import content_topics
    total_entities += db.session.scalar(select(func.count(Topic.id))) or 0
    orphans += db.session.scalar(
        select(func.count(Topic.id)).where(
            ~db.session.query(content_topics.c.content_id).filter(content_topics.c.topic_id == Topic.id).exists()
        )
    ) or 0
    
    # Sections
    total_entities += db.session.scalar(select(func.count(Section.id))) or 0
    orphans += db.session.scalar(
        select(func.count(Section.id)).where(
            ~db.session.query(Content.id).filter(Content.section_id == Section.id).exists()
        )
    ) or 0
    
    return jsonify({
        "total_content": total_content,
        "missing_category": missing_category,
        "missing_brand": missing_brand,
        "missing_section": missing_section,
        "total_entities": total_entities,
        "orphans": orphans
    })

# ─────────────────────────────────────────────
# TAXONOMY INSIGHTS (Phase 4)
# ─────────────────────────────────────────────

@bp.route("/insights/suggestions", methods=["GET"])
def insights_suggestions():
    from app.domains.relationships import content_brands
    # Get last 1000 unmapped contents for brand
    unmapped_brand = db.session.execute(
        select(Content).where(
            ~db.session.query(content_brands.c.brand_id).filter(content_brands.c.content_id == Content.id).exists()
        ).order_by(Content.id.desc()).limit(1000)
    ).scalars().all()
    
    # Get last 1000 unmapped contents for category
    unmapped_cat = db.session.execute(
        select(Content).where(Content.category_id == None).order_by(Content.id.desc()).limit(1000)
    ).scalars().all()

    brands = db.session.execute(select(Brand)).scalars().all()
    categories = db.session.execute(select(Category)).scalars().all()
    
    suggestions = []
    
    for c in unmapped_brand:
        if not c.title: continue
        title_lower = c.title.lower()
        for b in brands:
            # simple whole word match or strong substring
            if f" {b.name.lower()} " in f" {title_lower} ":
                suggestions.append({
                    "content_id": c.id,
                    "content_title": c.title,
                    "type": "Brand",
                    "suggested_id": b.id,
                    "suggested_name": b.name
                })
                break
                
    for c in unmapped_cat:
        if not c.title: continue
        title_lower = c.title.lower()
        for cat in categories:
            if f" {cat.name.lower()} " in f" {title_lower} ":
                suggestions.append({
                    "content_id": c.id,
                    "content_title": c.title,
                    "type": "Category",
                    "suggested_id": cat.id,
                    "suggested_name": cat.name
                })
                break

    return jsonify(suggestions[:50]) # Return top 50

@bp.route("/insights/coherence", methods=["GET"])
def insights_coherence():
    from app.domains.relationships import content_items
    
    # Find items that have a brand mapped, and find their parent contents
    # To keep it fast, we query contents that have items
    contents = db.session.execute(
        select(Content).where(
            db.session.query(content_items.c.item_id).filter(content_items.c.content_id == Content.id).exists()
        ).order_by(Content.id.desc()).limit(500)
    ).scalars().all()
    
    conflicts = []
    for c in contents:
        # get items for this content
        item_ids = db.session.scalars(select(content_items.c.item_id).where(content_items.c.content_id == c.id)).all()
        if not item_ids: continue
        
        items = db.session.execute(select(Item).where(Item.id.in_(item_ids))).scalars().all()
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
                
    return jsonify(conflicts[:50])

@bp.route("/insights/apply", methods=["POST"])
@admin_required
def insights_apply():
    data = request.json or {}
    content_id = data.get("content_id")
    type_ = data.get("type")
    suggested_id = data.get("suggested_id")
    
    if not content_id or not type_ or not suggested_id:
        return jsonify({"error": "Missing parameters"}), 400
        
    content = db.session.get(Content, content_id)
    if not content:
        return jsonify({"error": "Content not found"}), 404
        
    try:
        if type_ == "Brand":
            from app.domains.relationships import content_brands
            # Insert into content_brands
            exists = db.session.scalar(select(content_brands.c.content_id).where(content_brands.c.content_id == content_id, content_brands.c.brand_id == suggested_id))
            if not exists:
                db.session.execute(content_brands.insert().values(content_id=content_id, brand_id=suggested_id))
        elif type_ == "Category":
            content.category_id = suggested_id
            
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

def _get_facet_rows(model, domain_type, field_id_name):
    page, per_page = parse_pagination_params(default_per_page=50)
    search = request.args.get("search", "").strip()
    health = request.args.get("health")

    stmt = select(model).order_by(model.name.asc())
    if search:
        stmt = stmt.where(model.name.ilike(f"%{search}%"))
        
    field = getattr(Content, field_id_name)
    
    if health == "unused":
        stmt = stmt.where(~db.session.query(field).filter(field == model.id).exists())
        
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    
    item_ids = [a.id for a in pagination.items]
    content_counts = {}
    
    if item_ids:
        content_counts = dict(db.session.execute(select(field, func.count(Content.id)).where(field.in_(item_ids)).group_by(field)).all())
        
    serialized = []
    for a in pagination.items:
        c_count = content_counts.get(a.id, 0)
        h_status = "ok"
        if c_count == 0:
            h_status = "unused"
            
        data = {
            "id": a.id,
            "name": a.name,
            "content count": str(c_count),
            "health": h_status
        }
        serialized.append(data)

    html = render_template("admin/components/_rows.html", items=serialized, domain_type=domain_type)
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )


@bp.route("/gender_facets/rows", methods=["GET"])
def gender_facets_rows():
    return _get_facet_rows(GenderFacet, 'gender_facet', 'gender_id')

@bp.route("/intent_facets/rows", methods=["GET"])
def intent_facets_rows():
    return _get_facet_rows(IntentFacet, 'intent_facet', 'intent_id')

@bp.route("/price_tier_facets/rows", methods=["GET"])
def price_tier_facets_rows():
    return _get_facet_rows(PriceTierFacet, 'price_tier_facet', 'price_tier_id')

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
        if top_items:
            data["top clicked items"] = {"value": render_template("admin/components/_top_items_table.html", items=top_items), "is_custom": True}
        
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
        from app.domains.relationships import content_attributes
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

    data["top content"] = {"value": render_template("admin/components/content/_top_content_table.html", contents=top_contents), "is_custom": True}
    return data

def _get_taxonomy_inspect_table(entity, entity_type, metadata):
    from app.admin.helpers import format_status, format_featured
    from app.admin.tables import get_inspect_table
    
    data = {
        "id": f"#{entity.id}",
        "name": entity.name,
        "status": format_status(getattr(entity, "is_active", True)),
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
    elif entity_type == "attribute":
        data["slug"] = entity.slug
        data["category"] = entity.category.name if entity.category else "Global"
        return get_inspect_table("attributes", data)
    elif entity_type == "gender_facet":
        data["slug"] = entity.slug
        return get_inspect_table("gender_facets", data)
    elif entity_type == "intent_facet":
        data["slug"] = entity.slug
        return get_inspect_table("intent_facets", data)
    elif entity_type == "price_tier_facet":
        data["slug"] = entity.slug
        return get_inspect_table("price_tier_facets", data)

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

@bp.route("/attributes/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_attribute(id):
    attr, err = _get_entity_or_404(AttributeFacet, id, "Attribute")
    if err: return err, 404
    metadata = _get_taxonomy_related_metadata(attr, "attribute")
    inspect_table = _get_taxonomy_inspect_table(attr, "attribute", metadata)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table)

@bp.route("/gender_facets/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_gender_facet(id):
    facet, err = _get_entity_or_404(GenderFacet, id, "Gender Facet")
    if err: return err, 404
    metadata = _get_taxonomy_related_metadata(facet, "gender_facet")
    inspect_table = _get_taxonomy_inspect_table(facet, "gender_facet", metadata)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table)

@bp.route("/intent_facets/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_intent_facet(id):
    facet, err = _get_entity_or_404(IntentFacet, id, "Intent Facet")
    if err: return err, 404
    metadata = _get_taxonomy_related_metadata(facet, "intent_facet")
    inspect_table = _get_taxonomy_inspect_table(facet, "intent_facet", metadata)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table)

@bp.route("/price_tier_facets/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_price_tier_facet(id):
    facet, err = _get_entity_or_404(PriceTierFacet, id, "Price Tier Facet")
    if err: return err, 404
    metadata = _get_taxonomy_related_metadata(facet, "price_tier_facet")
    inspect_table = _get_taxonomy_inspect_table(facet, "price_tier_facet", metadata)
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
