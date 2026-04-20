from flask import Blueprint, render_template

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

@bp.route("/articles")
def dashboard_articles():
    return render_template("dashboard/core.html", title="Articles", domain="articles")


@bp.route("/items")
def dashboard_items():
    return render_template("dashboard/core.html", title="Items", domain="items")


@bp.route("/users")
def dashboard_users():
    return render_template("dashboard/core.html", title="Users", domain="users")


@bp.route("/interactions")
def dashboard_interactions():
    return render_template("dashboard/core.html", title="Interactions", domain="interactions")
