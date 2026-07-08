from flask import render_template, Blueprint
from app.web.routes.admin.tables import CRUD_TABLES, INSIGHTS_TABLES
from app.web.routes.admin.helpers import apply_admin_guard

bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)

apply_admin_guard(bp)

from app.application.analytics.admin import get_admin_dashboard_stats_data

@bp.route("/")
def home():
    stats_data = get_admin_dashboard_stats_data()
    return render_template(
        "admin/overview/overview.html", 
        title="Overview", 
        domain="home",
        stats=stats_data
    )




@bp.route("/distribution")
def dashboard_distribution():
    return render_template(
        "admin/distribution/distribution.html",
        title="Distribution & Publishing",
        domain="distribution",
        tables=INSIGHTS_TABLES
    )



@bp.route("/contents")
def dashboard_contents():
    return render_template(
        "admin/content_library/contents.html",
        title="Content Management",
        domain="contents",
        table=CRUD_TABLES["contents"],
    )


@bp.route("/items")
def dashboard_items():
    return render_template(
        "admin/product_intelligence/items.html",
        title="Product Management",
        domain="items",
        table=CRUD_TABLES["items"],
    )

@bp.route("/items/dashboard")
def dashboard_items_analytics():
    return render_template(
        "admin/product_intelligence/items_dashboard.html",
        title="Products Intelligence Dashboard",
        domain="items_dashboard"
    )


@bp.route("/sources")
def dashboard_sources():
    return render_template(
        "admin/acquisition/sources.html",
        title="Sources Management",
        domain="sources",
        table=CRUD_TABLES["sources"],
    )

@bp.route("/ingestions")
def dashboard_ingestions():
    return render_template(
        "admin/acquisition/ingestions.html",
        title="Ingestion Channels",
        domain="ingestions"
    )

@bp.route("/sources/quality")
def dashboard_sources_quality():
    return render_template(
        "admin/acquisition/quality.html",
        title="Quality & Freshness",
        domain="sources_quality"
    )


@bp.route("/stores")
def dashboard_stores():
    return render_template(
        "admin/product_intelligence/stores.html",
        title="Stores Management",
        domain="stores",
        table=CRUD_TABLES["stores"]        
    )

@bp.route("/stores/dashboard")
def dashboard_stores_analytics():
    return render_template(
        "admin/product_intelligence/stores_dashboard.html",
        title="Stores & Commercial Intelligence",
        domain="stores_dashboard"
    )


@bp.route("/taxonomy")
def dashboard_taxonomy():
    return render_template(
        "admin/taxonomy/taxonomy.html",
        title="Taxonomy Management",
        domain="taxonomy",
        tables=CRUD_TABLES,
    )


@bp.route("/users")
def dashboard_users():
    return render_template(
        "admin/audience/users.html",
        title="Users",
        domain="users",
        table=CRUD_TABLES["users"],
    )

@bp.route("/subscribers")
def dashboard_subscribers():
    return render_template(
        "admin/audience/subscribers.html",
        title="Newsletter Subscribers",
        domain="subscribers",
        table=CRUD_TABLES.get("subscribers", {}),
    )




@bp.route("/interactions")
def dashboard_interactions():
    return render_template(
        "admin/audience/interactions.html",
        title="Moderation & Interactions",
        domain="interactions",
        tables=CRUD_TABLES,
    )


@bp.route("/recommendations")
def dashboard_recommendations():
    return render_template(
        "admin/content_intelligence/recommendations.html",
        title="Recommendations",
        domain="recommendations",
        table=CRUD_TABLES["recommendations"],
    )


@bp.route("/settings")
def settings():
    return render_template("admin/settings.html", title="Settings", domain="settings")


@bp.route("/contents/<int:id>")
def content_detail(id):
    from app.application.content.admin import get_content_inspect_workflow
    from app.web.routes.admin.builders.content_builder import build_content_inspect_view_model
    from flask import abort
    
    aggregated_data = get_content_inspect_workflow(id)
    if not aggregated_data:
        abort(404)
        
    data = build_content_inspect_view_model(aggregated_data)
    return render_template("admin/components/_inspect.html", title=f"Content {id}", domain="contents", **data)


@bp.route("/items/<int:id>")
def item_detail(id):
    from app.application.item.admin import get_item_inspect_workflow
    from app.web.routes.admin.builders.item_builder import build_item_inspect_view_model
    from flask import abort
    
    aggregated_data = get_item_inspect_workflow(id)
    if not aggregated_data:
        abort(404)
        
    data = build_item_inspect_view_model(aggregated_data)
    return render_template("admin/components/_inspect.html", title=f"Product {id}", domain="items", **data)


@bp.route("/users/<int:id>")
def user_detail(id):
    from app.application.user.admin import get_user_inspect_workflow
    from app.web.routes.admin.builders.user_builder import build_user_inspect_view_model
    from flask import abort
    
    aggregated_data = get_user_inspect_workflow(id)
    if not aggregated_data:
        abort(404)
        
    data = build_user_inspect_view_model(aggregated_data)
    return render_template("admin/components/_inspect.html", title=f"User {id}", domain="users", **data)


@bp.route("/stores/<int:id>")
def store_detail(id):
    from app.application.item.admin import get_store_inspect_workflow
    from app.web.routes.admin.builders.item_builder import build_store_inspect_view_model
    from flask import abort
    
    aggregated_data = get_store_inspect_workflow(id)
    if not aggregated_data:
        abort(404)
        
    data = build_store_inspect_view_model(aggregated_data)
    return render_template("admin/components/_inspect.html", title=f"Store Details {id}", domain="stores", **data)


@bp.route("/sources/<int:id>")
def source_detail(id):
    from app.application.taxonomy.admin import get_source_inspect_workflow
    from app.web.routes.admin.builders.taxonomy_builder import build_source_inspect_view_model
    from flask import abort
    
    aggregated_data = get_source_inspect_workflow(id)
    if not aggregated_data:
        abort(404)
        
    data = build_source_inspect_view_model(aggregated_data)
    return render_template("admin/components/_inspect.html", title=f"Source Details {id}", domain="sources", **data)


@bp.route("/comments/<int:id>")
def comment_detail(id):
    from app.application.interaction.admin import get_comment_inspect_workflow
    from app.web.routes.admin.builders.interaction_builder import build_comment_inspect_view_model
    from flask import abort
    
    aggregated_data = get_comment_inspect_workflow(id)
    if not aggregated_data:
        abort(404)
        
    data = build_comment_inspect_view_model(aggregated_data)
    return render_template("admin/components/_inspect.html", title=f"Comment Details {id}", domain="comments", **data)


