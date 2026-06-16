from flask import render_template, Blueprint
from app.admin.tables import CRUD_TABLES
from app.core.decorators import admin_required

bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)

@bp.before_request
@admin_required
def require_admin():
    """Ensure all routes under /admin are strictly admin-only."""
    pass

@bp.route("/")
def home():
    return render_template("admin/dashboard/overview.html", title="Overview", domain="home")

@bp.route("/insights")
def dashboard_insights():
    return render_template("admin/control_panel/insights.html", title="Insights & Opportunities", domain="insights")


@bp.route("/contents")
def dashboard_contents():
    return render_template(
        "admin/control_panel/contents.html",
        title="Content Management",
        domain="contents",
        table=CRUD_TABLES["contents"],
    )


@bp.route("/items")
def dashboard_items():
    return render_template(
        "admin/control_panel/items.html",
        title="Product Management",
        domain="items",
        table=CRUD_TABLES["items"],
    )


@bp.route("/sources")
def dashboard_sources():
    return render_template(
        "admin/control_panel/sources.html",
        title="Sources Management",
        domain="sources",
        table=CRUD_TABLES["sources"],
    )


@bp.route("/stores")
def dashboard_stores():
    return render_template(
        "admin/control_panel/stores.html",
        title="Stores Management",
        domain="stores",
        table=CRUD_TABLES["stores"],
    )


@bp.route("/taxonomy")
def dashboard_taxonomy():
    return render_template(
        "admin/control_panel/taxonomy.html",
        title="Taxonomy Management",
        domain="taxonomy",
        tables=CRUD_TABLES,
    )


@bp.route("/users")
def dashboard_users():
    return render_template(
        "admin/control_panel/users.html",
        title="Users",
        domain="users",
        table=CRUD_TABLES["users"],
    )


@bp.route("/moderation")
def dashboard_moderation():
    return render_template(
        "admin/control_panel/interactions.html",
        title="Moderation & Interactions",
        domain="moderation",
        tables=CRUD_TABLES,
    )


@bp.route("/recommendations")
def dashboard_recommendations():
    return render_template(
        "admin/control_panel/recommendations.html",
        title="Recommendations",
        domain="recommendations",
        table=CRUD_TABLES["recommendations"],
    )


@bp.route("/settings")
def settings():
    return render_template("admin/control_panel/settings.html", title="Settings", domain="settings")
