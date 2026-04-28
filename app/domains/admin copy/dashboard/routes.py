from flask import render_template
from app.domains.admin import admin_bp as bp

@bp.route("/")
def home():
    return render_template("admin/dashboard/overview.html", title="Overview", domain="home")

@bp.route("/articles")
def dashboard_articles():
    return render_template("admin/dashboard/domain.html", title="Articles", domain="articles")


@bp.route("/items")
def dashboard_items():
    return render_template("admin/dashboard/domain.html", title="Items", domain="items")


@bp.route("/users")
def dashboard_users():
    return render_template("admin/dashboard/domain.html", title="Users", domain="users")


@bp.route("/interactions")
def dashboard_interactions():
    return render_template("admin/dashboard/domain.html", title="Interactions Analytics", domain="interactions")
