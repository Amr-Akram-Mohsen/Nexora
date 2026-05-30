from flask import render_template, Blueprint
from app.core.decorators import admin_required

bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)

# @bp.before_request
# @admin_required
# def require_admin():
#     """Ensure all routes under /admin are strictly admin-only."""
#     pass

@bp.route("/")
def home():
    return render_template("admin/dashboard/overview.html", title="Overview", domain="home")

@bp.route("/contents")
def dashboard_contents():
    return render_template("admin/control_panel/contents.html", title="Content Management", domain="contents")


@bp.route("/items")
def dashboard_items():
    return render_template("admin/dashboard/domain.html", title="Items", domain="items")


@bp.route("/users")
def dashboard_users():
    return render_template("admin/control_panel/users.html", title="Users", domain="users")


@bp.route("/interactions")
def dashboard_interactions():
    return render_template("admin/dashboard/domain.html", title="Interactions Analytics", domain="interactions")


@bp.route("/settings")
def settings():
    return render_template("admin/control_panel/settings.html", title="Settings", domain="settings")
