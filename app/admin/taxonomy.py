# app/admin/taxonomy.py
from flask import Blueprint, jsonify, request, render_template
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.taxonomy.models import Category, Brand, Topic, Section
from app.shared.utils.slug import generate_slug
from app.admin.helpers import parse_pagination_params, make_rows_response
from sqlalchemy import select, func
from app.domains.content.models.content import Content
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
    serialized = [_serialize_category(c) for c in pagination.items]

    html = render_template("admin/control_panel/taxonomy/_categories_rows.html", items=serialized)
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
    serialized = [_serialize_brand(b) for b in pagination.items]

    html = render_template("admin/control_panel/taxonomy/_brands_rows.html", items=serialized)
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
    serialized = [_serialize_topic(t) for t in pagination.items]

    html = render_template("admin/control_panel/taxonomy/_topics_rows.html", items=serialized)
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
    serialized = [_serialize_section(s) for s in pagination.items]

    html = render_template("admin/control_panel/taxonomy/_sections_rows.html", items=serialized)
    return make_rows_response(
        html,
        total=pagination.total,
        pages=pagination.pages,
        page=pagination.page,
    )

# ─────────────────────────────────────────────
# INSPECT ENDPOINTS
# ─────────────────────────────────────────────

@bp.route("/categories/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_category(id):
    cat = db.session.get(Category, id)
    if not cat:
        return "Category not found", 404
    content_count = db.session.query(func.count(Content.id)).filter(Content.category_id == id).scalar()
    item_count = db.session.query(func.count(Item.id)).filter(Item.category_id == id).scalar()
    return render_template(
        "admin/control_panel/taxonomy/_category_inspect.html",
        category=cat,
        content_count=content_count,
        item_count=item_count
    )

@bp.route("/brands/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_brand(id):
    brand = db.session.get(Brand, id)
    if not brand:
        return "Brand not found", 404
    content_count = db.session.query(Content).with_parent(brand, "contents").count()
    item_count = db.session.query(func.count(Item.id)).filter(Item.brand_id == id).scalar()
    return render_template(
        "admin/control_panel/taxonomy/_brand_inspect.html",
        brand=brand,
        content_count=content_count,
        item_count=item_count
    )

@bp.route("/topics/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_topic(id):
    topic = db.session.get(Topic, id)
    if not topic:
        return "Topic not found", 404
    content_count = db.session.query(Content).with_parent(topic, "contents").count()
    return render_template(
        "admin/control_panel/taxonomy/_topic_inspect.html",
        topic=topic,
        content_count=content_count
    )

@bp.route("/sections/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_section(id):
    section = db.session.get(Section, id)
    if not section:
        return "Section not found", 404
    content_count = db.session.query(func.count(Content.id)).filter(Content.section_id == id).scalar()
    return render_template(
        "admin/control_panel/taxonomy/_section_inspect.html",
        section=section,
        content_count=content_count
    )
