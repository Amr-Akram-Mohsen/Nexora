from flask import render_template, Blueprint

bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)

@bp.route("/")
def home():
    return render_template("admin/dashboard/overview.html", title="Overview", domain="home")

@bp.route("/contents")
def dashboard_contents():
    return render_template("admin/dashboard/domain.html", title="Content", domain="contents")


@bp.route("/items")
def dashboard_items():
    return render_template("admin/dashboard/domain.html", title="Items", domain="items")


@bp.route("/users")
def dashboard_users():
    return render_template("admin/dashboard/domain.html", title="Users", domain="users")


@bp.route("/interactions")
def dashboard_interactions():
    return render_template("admin/dashboard/domain.html", title="Interactions Analytics", domain="interactions")
