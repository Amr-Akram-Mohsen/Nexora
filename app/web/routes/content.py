from flask import Blueprint, request, render_template, abort
from app.application.content.get_feed import get_feed_data
from app.application.content.get_article_page import get_article_page_data
from flask_login import current_user
from app.shared.request import get_client_ip

bp = Blueprint("content", __name__)

@bp.route("/sections/<section_slug>")
def sections(section_slug):
    from app.web.helpers.content import parse_active_filters
    active_filters = parse_active_filters(['category', 'topic', 'brand'])
    page = request.args.get('page', 1, type=int)

    data = get_feed_data(section_slug, active_filters, page=page)
    if not data:
        abort(404)

    return render_template(
        "content/listing/catalog-page.html",
        target_type="contents",
        active_filters=active_filters,
        **data
    )

@bp.route("/contents/<int:content_id>")
def content_page(content_id):
    from app.application.content.get_article_page import record_article_view
    from app.core.extensions import db
    
    user = current_user if current_user.is_authenticated else None
    ip_address = None if user else get_client_ip()
    
    data = get_article_page_data(content_id)
    if not data:
        abort(404)

    # Orchestrate Query + Command
    record_article_view(content_id, user, ip_address)
    db.session.commit()
   
    return render_template(
        "content/dispatcher/page.html",
        **data
    )


