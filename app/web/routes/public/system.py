import logging
from flask import (
    Blueprint,
    request,
    render_template,
    jsonify,
    current_app,
    make_response,
    url_for,
)
import os
from datetime import datetime
from app.application.system.home import get_home_page_data
from app.application.system.contact import send_contact_message_workflow

from app.shared.utils.logging import log_route_start, log_route_success, log_route_error
from app.core.extensions import limiter
from . import PUBLIC_TEMPLATES

logger = logging.getLogger(__name__)

bp = Blueprint("system", __name__, template_folder=PUBLIC_TEMPLATES)


@bp.app_context_processor
def inject_global_context():
    from app.core.context import get_global_context

    return get_global_context()


@bp.route("/set-country", methods=["POST"])
def set_country():
    country = request.json.get("country")
    response = jsonify({"success": True})
    if country:
        response.set_cookie("country", country.lower(), max_age=60 * 60 * 24 * 365)
    else:
        response.delete_cookie("country")
    return response


@bp.route("/", methods=["GET", "HEAD"])
def home():
    if request.method == "HEAD":
        return "", 200
        
    log_route_start(logger, "/")
    data = get_home_page_data()
    data.setdefault("sections", [])
    data.setdefault("trending", [])
    
    from flask_login import current_user
    if current_user.is_authenticated:
        from app.application.interaction.public import get_reading_history_workflow
        from app.application.recommendation.personalization import get_personalized_feed_workflow
        data["recently_viewed"] = get_reading_history_workflow(current_user.id, limit=8)
        data["recommended_items"] = get_personalized_feed_workflow(current_user.id, limit=12)
        
    log_route_success(logger, "/", template="public/index.html")
    return render_template("public/index.html", **data)

@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/contact")
def contact():
    return render_template("contact.html")


@bp.route("/contact", methods=["POST"])
@limiter.limit("5 per minute")
def send_contact_message():
    data = {
        k: request.form.get(k, "").strip()
        for k in ("name", "email", "subject", "message")
    }

    success, message = send_contact_message_workflow(
        data, request.remote_addr, request.headers.get("User-Agent")
    )

    return jsonify({"success": success, "message" if success else "error": message})


@bp.route("/privacy")
def privacy():
    return render_template("privacy.html")


@bp.route("/terms")
def terms():
    return render_template("terms.html")


@bp.route("/affiliate")
def affiliate():
    return render_template("affiliate.html")

@bp.route("/newsletter")
def newsletter():
    return render_template("newsletter.html")


from flask import send_from_directory

@bp.route("/sitemap.xml")
def sitemap():
    static_folder = os.path.join(current_app.static_folder, "sitemaps")
    index_path = os.path.join(static_folder, "sitemap_index.xml")
    
    if os.path.exists(index_path):
        return send_from_directory(static_folder, "sitemap_index.xml", mimetype="application/xml")
        
    # Fallback if no static sitemap exists (can happen before first cron run)
    return make_response("Sitemap not generated yet. Run flask generate-sitemap.", 503)

@bp.route("/sitemap_<int:chunk>.xml")
def sitemap_chunk(chunk):
    static_folder = os.path.join(current_app.static_folder, "sitemaps")
    chunk_filename = f"sitemap_{chunk}.xml"
    
    if os.path.exists(os.path.join(static_folder, chunk_filename)):
        return send_from_directory(static_folder, chunk_filename, mimetype="application/xml")
        
    return make_response("Sitemap chunk not found.", 404)
