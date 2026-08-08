# app/admin/taxonomy.py
from flask import Blueprint, jsonify, request, render_template
from app.core.decorators import admin_required
from app.web.routes.admin.helpers import apply_admin_guard
from app.core.extensions import db
from app.domains.taxonomy.models import Category, Brand, Entity, Section, Source, AttributeFacet, GenderFacet, IntentFacet, PriceTierFacet
from app.shared.utils.slug import generate_slug
from app.web.routes.admin.helpers import parse_pagination_params, render_admin_rows_response
from sqlalchemy import select, func, update
import difflib
from app.domains.content.models import Content
from app.domains.product.models import Product
from app.domains.analytics.taxonomy_intelligence import get_taxonomy_intelligence
from app.domains.taxonomy.service.query import paginate_taxonomy_entity
from app.domains.taxonomy.service.admin import (
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
from app.domains.taxonomy.serializers import (
    serialize_taxonomy, serialize_category, serialize_brand,
    serialize_topic, serialize_section, serialize_attribute
)

bp = Blueprint("api_taxonomy", __name__, url_prefix="/admin/taxonomy")


apply_admin_guard(bp)


# ─────────────────────────────────────────────
# INTELLIGENCE DASHBOARD
# ─────────────────────────────────────────────
@bp.route("/intelligence", methods=["GET"])
def intelligence_dashboard():
    data = get_taxonomy_intelligence()
    return render_template("admin/taxonomy/intelligence.html", data=data)

@bp.route("/stats", methods=["GET"])
def taxonomy_stats():
    """Returns top-level KPI stats for the taxonomy dashboard."""
    data = get_admin_taxonomy_analytics()
    return jsonify({
        "total_entities": data["health"]["total_entities"],
        "orphan_entities": data["health"]["orphan_entities"],
        "orphan_pct": data["health"]["orphan_pct"],
        "missing_category": data["content_coverage"]["missing_category"],
        "missing_section": data["content_coverage"]["missing_section"],
        "missing_brand": data["content_coverage"]["missing_brand"]
    })

# ─────────────────────────────────────────────
# CATEGORIES
# ─────────────────────────────────────────────

@bp.route("/categories", methods=["GET"])
def list_categories():
    search = request.args.get("search", "").strip()
    cats = get_admin_categories(search)
    return jsonify([serialize_category(c) for c in cats])


@bp.route("/categories", methods=["POST"])
@admin_required
def create_category():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    try:
        cat = create_admin_category(name, data.get("is_active", True))
        return jsonify(serialize_category(cat)), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 409


@bp.route("/categories/<int:id>", methods=["PATCH"])
@admin_required
def update_category(id):
    data = request.get_json() or {}
    cat = update_admin_category(id, data)
    if not cat:
        return jsonify({"error": "Not found"}), 404
    return jsonify(serialize_category(cat))


@bp.route("/categories/<int:id>", methods=["DELETE"])
@admin_required
def delete_category(id):
    cat = delete_admin_category(id)
    if not cat:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"success": True, "message": f"Category '{cat.name}' deleted."})




# ─────────────────────────────────────────────
# BRANDS
# ─────────────────────────────────────────────

@bp.route("/brands", methods=["GET"])
def list_brands():
    search = request.args.get("search", "").strip()
    brands = get_admin_brands(search)
    return jsonify([serialize_brand(b) for b in brands])


@bp.route("/brands", methods=["POST"])
@admin_required
def create_brand():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    try:
        brand = create_admin_brand(name, data.get("industry"), data.get("is_active", True))
        return jsonify(serialize_brand(brand)), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 409


@bp.route("/brands/<int:id>", methods=["PATCH"])
@admin_required
def update_brand(id):
    data = request.get_json() or {}
    brand = update_admin_brand(id, data)
    if not brand:
        return jsonify({"error": "Not found"}), 404
    return jsonify(serialize_brand(brand))


@bp.route("/brands/<int:id>", methods=["DELETE"])
@admin_required
def delete_brand(id):
    brand = delete_admin_brand(id)
    if not brand:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"success": True, "message": f"Brand '{brand.name}' deleted."})


# ─────────────────────────────────────────────
# TOPICS
# ─────────────────────────────────────────────

@bp.route("/topics", methods=["GET"])
def list_topics():
    search = request.args.get("search", "").strip()
    topics = get_admin_topics(search)
    return jsonify([serialize_topic(t) for t in topics])


@bp.route("/topics", methods=["POST"])
@admin_required
def create_topic():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    try:
        topic = create_admin_topic(name, data.get("is_active", True))
        return jsonify(serialize_topic(topic)), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 409


@bp.route("/topics/<int:id>", methods=["PATCH"])
@admin_required
def update_topic(id):
    data = request.get_json() or {}
    topic = update_admin_topic(id, data)
    if not topic:
        return jsonify({"error": "Not found"}), 404
    return jsonify(serialize_topic(topic))


@bp.route("/topics/<int:id>", methods=["DELETE"])
@admin_required
def delete_topic(id):
    topic = delete_admin_topic(id)
    if not topic:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"success": True, "message": f"Topic '{topic.name}' deleted."})


# ─────────────────────────────────────────────
# SECTIONS
# ─────────────────────────────────────────────

@bp.route("/sections", methods=["GET"])
def list_sections():
    search = request.args.get("search", "").strip()
    sections = get_admin_sections(search)
    return jsonify([serialize_section(s) for s in sections])


@bp.route("/sections/<int:id>", methods=["PATCH"])
@admin_required
def update_section(id):
    data = request.get_json() or {}
    section = update_admin_section(id, data)
    if not section:
        return jsonify({"error": "Not found"}), 404
    return jsonify(serialize_section(section))


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

    from app.application.taxonomy.admin import get_category_rows_workflow
    serialized, pagination = get_category_rows_workflow(page, per_page, search, status, health)

    return render_admin_rows_response(
        serialized, 'category',
        total=pagination.total, pages=pagination.pages, page=pagination.page
    )


@bp.route("/brands/rows", methods=["GET"])
def brands_rows():
    """Return server-rendered HTML rows partial for brands AJAX injection."""

    page, per_page = parse_pagination_params(default_per_page=50)
    search = request.args.get("search", "").strip()
    status = request.args.get("status")
    health = request.args.get("health")

    from app.application.taxonomy.admin import get_brand_rows_workflow
    serialized, pagination = get_brand_rows_workflow(page, per_page, search, status, health)

    return render_admin_rows_response(
        serialized, 'brand',
        total=pagination.total, pages=pagination.pages, page=pagination.page
    )


@bp.route("/topics/rows", methods=["GET"])
def topics_rows():
    """Return server-rendered HTML rows partial for topics AJAX injection."""

    page, per_page = parse_pagination_params(default_per_page=50)
    search = request.args.get("search", "").strip()
    status = request.args.get("status")
    health = request.args.get("health")

    from app.application.taxonomy.admin import get_topic_rows_workflow
    serialized, pagination = get_topic_rows_workflow(page, per_page, search, status, health)

    return render_admin_rows_response(
        serialized, 'topic',
        total=pagination.total, pages=pagination.pages, page=pagination.page
    )


@bp.route("/sections/rows", methods=["GET"])
def sections_rows():
    """Return server-rendered HTML rows partial for sections AJAX injection."""
    page, per_page = parse_pagination_params(default_per_page=50)
    search = request.args.get("search", "").strip()
    status = request.args.get("status")
    health = request.args.get("health")

    from app.application.taxonomy.admin import get_section_rows_workflow
    serialized, pagination = get_section_rows_workflow(page, per_page, search, status, health)

    return render_admin_rows_response(
        serialized, 'section',
        total=pagination.total, pages=pagination.pages, page=pagination.page
    )

# ─────────────────────────────────────────────
# ATTRIBUTES
# ─────────────────────────────────────────────

@bp.route("/attributes", methods=["GET"])
def list_attributes():
    search = request.args.get("search", "").strip()
    attrs = get_admin_attributes(search)
    return jsonify([serialize_attribute(a) for a in attrs])

@bp.route("/attributes", methods=["POST"])
@admin_required
def create_attribute():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    try:
        attr = create_admin_attribute(name, data.get("category_id"))
        return jsonify(serialize_attribute(attr)), 201
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
        return jsonify(serialize_attribute(attr))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@bp.route("/attributes/<int:id>", methods=["DELETE"])
@admin_required
def delete_attribute(id):
    attr = delete_admin_attribute(id)
    if not attr:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"success": True, "message": f"Attribute '{attr.name}' deleted."})


@bp.route("/attributes/rows", methods=["GET"])
def attributes_rows():
    page, per_page = parse_pagination_params(default_per_page=50)
    search = request.args.get("search", "").strip()
    health = request.args.get("health")

    from app.application.taxonomy.admin import get_attribute_rows_workflow
    serialized, pagination = get_attribute_rows_workflow(page, per_page, search, health)

    return render_admin_rows_response(
        serialized, 'attribute',
        total=pagination.total, pages=pagination.pages, page=pagination.page
    )

# ─────────────────────────────────────────────
# CONTENT FACETS (READ-ONLY)
# ─────────────────────────────────────────────


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

    from app.application.taxonomy.admin import get_facet_rows_workflow
    serialized, pagination = get_facet_rows_workflow(model, field_id_name, page, per_page, search, health)

    return render_admin_rows_response(
        serialized, domain_type,
        total=pagination.total, pages=pagination.pages, page=pagination.page
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

def _render_taxonomy_inspect(model, id, entity_name, entity_type):
    from app.web.routes.admin.builders.taxonomy_builder import build_taxonomy_inspect_view_model
    entity, err = _get_entity_or_404(model, id, entity_name)
    if err: return err, 404
    metadata = get_admin_taxonomy_related_metadata(entity, entity_type)
    data = build_taxonomy_inspect_view_model(entity, entity_type, metadata)
    return render_template("admin/components/_inspect.html", **data)

@bp.route("/categories/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_category(id):
    return _render_taxonomy_inspect(Category, id, "Category", "category")

@bp.route("/brands/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_brand(id):
    return _render_taxonomy_inspect(Brand, id, "Brand", "brand")

@bp.route("/topics/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_topic(id):
    return _render_taxonomy_inspect(Entity, id, "Topic", "topic")

@bp.route("/sections/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_section(id):
    return _render_taxonomy_inspect(Section, id, "Section", "section")

@bp.route("/attributes/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_attribute(id):
    return _render_taxonomy_inspect(AttributeFacet, id, "Attribute", "attribute")

@bp.route("/gender_facets/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_gender_facet(id):
    return _render_taxonomy_inspect(GenderFacet, id, "Gender Facet", "gender_facet")

@bp.route("/intent_facets/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_intent_facet(id):
    return _render_taxonomy_inspect(IntentFacet, id, "Intent Facet", "intent_facet")

@bp.route("/price_tier_facets/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_price_tier_facet(id):
    return _render_taxonomy_inspect(PriceTierFacet, id, "Price Tier Facet", "price_tier_facet")

@bp.route("/sources/<int:id>/inspect", methods=["GET"])
@admin_required
def inspect_source(id):
    source, err = _get_entity_or_404(Source, id, "Source")
    if err: return err, 404
    from app.web.routes.admin.tables import get_inspect_table
    
    data = get_admin_source_metadata(source)
    
    inspect_table = get_inspect_table("sources", data)
    return render_template("admin/components/_inspect.html", inspect_table=inspect_table)
