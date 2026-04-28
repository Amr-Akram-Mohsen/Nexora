from flask import render_template
from app.domains.admin import admin_bp as bp

@bp.route("/control-panel/users")
def control_users():
    return render_template("admin/control_panel/users.html", domain="control_users")

@bp.route("/control-panel/settings")
def control_settings():
    return render_template("admin/control_panel/settings.html", domain="control_settings")
