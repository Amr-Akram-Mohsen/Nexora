# app/admin/taxonomy.py
from flask import Blueprint, jsonify, request, render_template
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.taxonomy.models import Category, Brand, Topic, Section, Source, AttributeFacet, GenderFacet, IntentFacet, PriceTierFacet
from app.shared.utils.slug import generate_slug
from app.web.routes.admin.helpers import parse_pagination_params, make_rows_response
from sqlalchemy import select, func, update
import difflib
from app.domains.content.models import Content
from app.domains.item.models import Item
from app.domains.analytics.taxonomy_intelligence import get_taxonomy_intelligence
from app.domains.taxonomy.service.admin import (
    get_admin_categories_paginated, get_admin_brands_paginated,
    get_admin_topics_paginated, get_admin_sections_paginated,
    get_admin_attributes_paginated, get_admin_facet_paginated,
    get_admin_categories,
    get_admin_brands,
    get_admin_topics,
    get_admin_sections,
    get_admin_attributes,
    get_admin_taxonomy_analytics, get_admin_entity_or_404, get_admin_taxonomy_related_metadata,
    get_admin_source_metadata
)
from app.application.taxonomy.admin import (
    create_admin_category, update_admin_category, delete_admin_category,
    create_admin_brand, update_admin_brand, delete_admin_brand,
    create_admin_topic, update_admin_topic, delete_admin_topic,
    update_admin_section,
    create_admin_attribute, update_admin_attribute, delete_admin_attribute,
    apply_taxonomy_insight_workflow
)

bp = Blueprint("api_taxonomy", __name__, url_prefix="/admin/taxonomy")


@bp.before_request
@admin_required
def require_admin():
    """Ensure all taxonomy management endpoints require admin privilege."""
    pass


# ─────────────────────────────────────────────
# INTELLIGENCE DASHBOARD
# ─────────────────────────────────────────────
@bp.route("/intelligence", methods=["GET"])
def intelligence_dashboard():
    data = get_taxonomy_intelligence()
    return render_template("admin/taxonomy/intelligence.html", data=data)

# ─────────────────────────────────────────────
# CATEGORIES
# ─────────────────────────────────────────────

@bp.route("/categories", methods=["GET"])
def list_categories():
    search = request.args.get("search", "").strip()
    cats = get_admin_categories(search)
    return jsonify([_serialize_category(c) for c in cats])


@bp.route("/categories", methods=["POST"])
@admin_required
def create_category():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    try:
        cat = create_admin_category(name, data.get("is_active", True))
        return jsonify(_serialize_category(cat)), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 409


@bp.route("/categories/<int:id>", methods=["PATCH"])
@admin_required
def update_category(id):
    data = request.get_json() or {}
    cat = update_admin_category(id, data)
    if not cat:
        return jsonify({"error": "Not found"}), 404
    return jsonify(_serialize_category(cat))


@bp.route("/categories/<int:id>", methods=["DELETE"])
@admin_required
def delete_category(id):
    cat = delete_admin_category(id)
    if not cat:
        return jsonify({"error": "Not found"}), 404
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
    brands = get_admin_brands(search)
    return jsonify([_serialize_brand(b) for b in brands])


@bp.route("/brands", methods=["POST"])
@admin_required
def create_brand():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    try:
        brand = create_admin_brand(name, data.get("industry"), data.get("is_active", True))
        return jsonify(_serialize_brand(brand)), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 409


@bp.route("/brands/<int:id>", methods=["PATCH"])
@admin_required
def update_brand(id):
    data = request.get_json() or {}
    brand = update_admin_brand(id, data)
    if not brand:
        return jsonify({"error": "Not found"}), 404
    return jsonify(_serialize_brand(brand))


@bp.route("/brands/<int:id>", methods=["DELETE"])
@admin_required
def delete_brand(id):
    brand = delete_admin_brand(id)
    if not brand:
        return jsonify({"error": "Not found"}), 404
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
    topics = get_admin_topics(search)
    return jsonify([_serialize_topic(t) for t in topics])


@bp.route("/topics", methods=["POST"])
@admin_required
def create_topic():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    try:
        topic = create_admin_topic(name, data.get("is_active", True))
        return jsonify(_serialize_topic(topic)), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 409


@bp.route("/topics/<int:id>", methods=["PATCH"])
@admin_required
def update_topic(id):
    data = request.get_json() or {}
    topic = update_admin_topic(id, data)
    if not topic:
        return jsonify({"error": "Not found"}), 404
    return jsonify(_serialize_topic(topic))


@bp.route("/topics/<int:id>", methods=["DELETE"])
@admin_required
def delete_topic(id):
    topic = delete_admin_topic(id)
    if not topic:
        return jsonify({"error": "Not found"}), 404
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
    sections = get_admin_sections(search)
    return jsonify([_serialize_section(s) for s in sections])


@bp.route("/sections/<int:id>", methods=["PATCH"])
@admin_required
def update_section(id):
    data = request.get_json() or {}
    section = update_admin_section(id, data)
    if not section:
        return jsonify({"error": "Not found"}), 404
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

    pagination = get_admin_categories_paginated(page, per_page, search, status, health)
    item_ids = [c.id for c in pagination.items]
    from app.domains.taxonomy.service.metrics import get_category_metrics
    metrics = get_category_metrics(item_ids)
        
    serialized = []
    for c in pagination.items:
        m = metrics.get(c.id, {})
        c_count = m.get("content_count", 0)
        i_count = m.get("item_count", 0)
        child_count = m.get("children_count", 0)
        
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

    pagination = get_admin_brands_paginated(page, per_page, search, status, health)
    item_ids = [b.id for b in pagination.items]
    from app.domains.taxonomy.service.metrics import get_brand_metrics
    metrics = get_brand_metrics(item_ids)
        
    serialized = []
    for b in pagination.items:
        m = metrics.get(b.id, {})
        c_count = m.get("content_count", 0)
        i_count = m.get("item_count", 0)
        
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

    pagination = get_admin_topics_paginated(page, per_page, search, status, health)
    item_ids = [t.id for t in pagination.items]
    from app.domains.taxonomy.service.metrics import get_topic_metrics
    metrics = get_topic_metrics(item_ids)
        
    serialized = []
    for t in pagination.items:
        m = metrics.get(t.id, {})
        c_count = m.get("content_count", 0)
        cat_count = m.get("category_spread", 0)
        
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

    pagination = get_admin_sections_paginated(page, per_page, search, status, health)
    item_ids = [s.id for s in pagination.items]
    from app.domains.taxonomy.service.metrics import get_section_metrics
    metrics = get_section_metrics(item_ids)
        
    serialized = []
    for s in pagination.items:
        m = metrics.get(s.id, {})
        c_count = m.get("content_count", 0)
        cat_count = m.get("category_spread", 0)
        
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
    attrs = get_admin_attributes(search)
    return jsonify([_serialize_attribute(a) for a in attrs])

@bp.route("/attributes", methods=["POST"])
@admin_required
def create_attribute():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    try:
        attr = create_admin_attribute(name, data.get("category_id"))
        return jsonify(_serialize_attribute(attr)), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@bp.route("/attributes/<int:id>", methods=["PATCH"])
@admin_required
def update_attribute(id):
    data = request.get_json() or {}
    try:
        attr = update_admin_attribute(id, data)
        if not attr:
            return jsonify({"error": "Not found"}), 404
        return jsonify(_serialize_attribute(attr))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@bp.route("/attributes/<int:id>", methods=["DELETE"])
@admin_required
def delete_attribute(id):
    attr = delete_admin_attribute(id)
    if not attr:
        return jsonify({"error": "Not found"}), 404
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

    pagination = get_admin_attributes_paginated(page, per_page, search, health)
    item_ids = [a.id for a in pagination.items]
    from app.domains.taxonomy.service.metrics import get_attribute_metrics
    metrics = get_attribute_metrics(item_ids)
        
    serialized = []
    for a in pagination.items:
        m = metrics.get(a.id, {})
        c_count = m.get("content_count", 0)
        
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

    pagination = get_admin_facet_paginated(model_class, field_name, page, per_page, search, health)
    item_ids = [f.id for f in pagination.items]
    from app.domains.taxonomy.service.metrics import get_facet_metrics
    metrics = get_facet_metrics(item_ids, field_name)
        
    serialized = []
    for f in pagination.items:
        m = metrics.get(f.id, {})
        c_count = m.get("content_count", 0)
        
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
    
    from app.domains.taxonomy.service.duplicates import DOMAIN_MAP, detect_taxonomy_duplicates
    
    if domain not in DOMAIN_MAP:
        return jsonify({"error": "Invalid domain"}), 400
        
    try:
        data = detect_taxonomy_duplicates(domain)
        return render_template("admin/taxonomy/_duplicates.html", data=data, domain=domain)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@bp.route("/merge", methods=["POST"])
@admin_required
def taxonomy_merge():
    data = request.json or {}
    domain = data.get("domain")
    source_id = data.get("source_id")
    target_id = data.get("target_id")
    
    if not domain or not source_id or not target_id:
        return jsonify({"error": "Missing parameters"}), 400
        
    from app.domains.taxonomy.service.duplicates import merge_taxonomy_entities
    try:
        merge_taxonomy_entities(domain, source_id, target_id)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────────
# ANALYTICS DASHBOARD
# ─────────────────────────────────────────────

@bp.route("/analytics", methods=["GET"])
def taxonomy_analytics():
    metrics = get_admin_taxonomy_analytics()
    data = {
        "total_content": metrics["content_coverage"]["total_content"],
        "missing_category": metrics["content_coverage"]["missing_category"],
        "missing_brand": metrics["content_coverage"]["missing_brand"],
        "missing_section": metrics["content_coverage"]["missing_section"],
        "total_entities": metrics["health"]["total_entities"],
        "orphans": metrics["health"]["orphan_entities"]
    }
    return render_template("admin/taxonomy/_analytics_dashboard.html", data=data)

# ─────────────────────────────────────────────
# TAXONOMY INSIGHTS (Phase 4)
# ─────────────────────────────────────────────

@bp.route("/insights/suggestions", methods=["GET"])
def insights_suggestions():
    from app.domains.taxonomy.service.insights import get_taxonomy_insights_suggestions
    data = get_taxonomy_insights_suggestions()
    return render_template("admin/taxonomy/_insights_suggestions.html", data=data)

@bp.route("/insights/coherence", methods=["GET"])
def insights_coherence():
    from app.domains.taxonomy.service.insights import get_taxonomy_insights_coherence
    data = get_taxonomy_insights_coherence()
    return render_template("admin/taxonomy/_insights_coherence.html", data=data)

@bp.route("/insights/apply", methods=["POST"])
@admin_required
def insights_apply():
    data = request.json or {}
    content_id = data.get("content_id")
    type_ = data.get("type")
    suggested_id = data.get("suggested_id")
    
    if not content_id or not type_ or not suggested_id:
        return jsonify({"error": "Missing parameters"}), 400
        
    try:
        apply_taxonomy_insight_workflow(content_id, type_, suggested_id)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _get_facet_rows(model, domain_type, field_id_name):
    page, per_page = parse_pagination_params(default_per_page=50)
    search = request.args.get("search", "").strip()
    health = request.args.get("health")

    pagination = get_admin_facet_paginated(model, field_id_name, page, per_page, search, health)
    item_ids = [a.id for a in pagination.items]
    
    from app.domains.taxonomy.service.metrics import get_facet_metrics
    metrics = get_facet_metrics(item_ids, field_id_name)
    
    serialized = []
    for a in pagination.items:
        m = metrics.get(a.id, {})
        c_count = m.get("content_count", 0)
        
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
    entity = get_admin_entity_or_404(model, id)
    if not entity:
        return None, f"{entity_name} not found."
    return entity, None

def _get_taxonomy_inspect_table(entity, entity_type, metadata):
    from app.web.routes.admin.helpers import format_status, format_featured
    from app.web.routes.admin.tables import get_inspect_table
    
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
    metadata = get_admin_taxonomy_related_metadata(cat, "category")
    top_contents = metadata.pop("_top_contents", None)
    inspect_table = _get_taxonomy_inspect_table(cat, "category", metadata)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table, top_contents=top_contents)

@bp.route("/brands/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_brand(id):
    brand, err = _get_entity_or_404(Brand, id, "Brand")
    if err: return err, 404
    metadata = get_admin_taxonomy_related_metadata(brand, "brand")
    top_contents = metadata.pop("_top_contents", None)
    top_items = metadata.pop("_top_items", None)
    inspect_table = _get_taxonomy_inspect_table(brand, "brand", metadata)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table, top_contents=top_contents, top_items=top_items)

@bp.route("/topics/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_topic(id):
    topic, err = _get_entity_or_404(Topic, id, "Topic")
    if err: return err, 404
    metadata = get_admin_taxonomy_related_metadata(topic, "topic")
    top_contents = metadata.pop("_top_contents", None)
    inspect_table = _get_taxonomy_inspect_table(topic, "topic", metadata)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table, top_contents=top_contents)

@bp.route("/sections/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_section(id):
    section, err = _get_entity_or_404(Section, id, "Section")
    if err: return err, 404
    metadata = get_admin_taxonomy_related_metadata(section, "section")
    top_contents = metadata.pop("_top_contents", None)
    inspect_table = _get_taxonomy_inspect_table(section, "section", metadata)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table, top_contents=top_contents)

@bp.route("/attributes/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_attribute(id):
    attr, err = _get_entity_or_404(AttributeFacet, id, "Attribute")
    if err: return err, 404
    metadata = get_admin_taxonomy_related_metadata(attr, "attribute")
    top_contents = metadata.pop("_top_contents", None)
    inspect_table = _get_taxonomy_inspect_table(attr, "attribute", metadata)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table, top_contents=top_contents)

@bp.route("/gender_facets/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_gender_facet(id):
    facet, err = _get_entity_or_404(GenderFacet, id, "Gender Facet")
    if err: return err, 404
    metadata = get_admin_taxonomy_related_metadata(facet, "gender_facet")
    top_contents = metadata.pop("_top_contents", None)
    inspect_table = _get_taxonomy_inspect_table(facet, "gender_facet", metadata)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table, top_contents=top_contents)

@bp.route("/intent_facets/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_intent_facet(id):
    facet, err = _get_entity_or_404(IntentFacet, id, "Intent Facet")
    if err: return err, 404
    metadata = get_admin_taxonomy_related_metadata(facet, "intent_facet")
    top_contents = metadata.pop("_top_contents", None)
    inspect_table = _get_taxonomy_inspect_table(facet, "intent_facet", metadata)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table, top_contents=top_contents)

@bp.route("/price_tier_facets/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_price_tier_facet(id):
    facet, err = _get_entity_or_404(PriceTierFacet, id, "Price Tier Facet")
    if err: return err, 404
    metadata = get_admin_taxonomy_related_metadata(facet, "price_tier_facet")
    top_contents = metadata.pop("_top_contents", None)
    inspect_table = _get_taxonomy_inspect_table(facet, "price_tier_facet", metadata)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table, top_contents=top_contents)

@bp.route("/sources/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_source(id):
    source, err = _get_entity_or_404(Source, id, "Source")
    if err: return err, 404
    from app.web.routes.admin.tables import get_inspect_table
    
    data = get_admin_source_metadata(source)
    
    inspect_table = get_inspect_table("sources", data)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table)
