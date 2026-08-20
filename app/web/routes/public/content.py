"""
Public content catalog and detail page routes.
"""
import logging
from flask import Blueprint, request, render_template, abort, jsonify
from flask_login import current_user

from app.web.routes.constants import PUBLIC_TEMPLATES
from app.application.content.public import (
    get_feed_data,
    get_source_feed_data,
    get_globe_data_workflow,
    get_content_page_data,
    record_content_view,
)
from app.web.helpers.filters import parse_active_filters
from app.shared.request import get_client_ip
from app.shared.utils.logging import log_route_start, log_route_success, log_route_error

logger = logging.getLogger(__name__)

bp = Blueprint("content", __name__, template_folder=PUBLIC_TEMPLATES)


@bp.route("/sections/<section_slug>")
def sections(section_slug):
    active_filters = parse_active_filters(
        list_names=["category", "entity", "intent", "price_tier", "type", "attributes", "source", "event", "author", "location"]
    )
    page = request.args.get("page", 1, type=int)

    log_route_start(logger, f"/sections/{section_slug}", page=page, filters=active_filters)
    try:
        data = get_feed_data(section_slug, active_filters, page=page)
        if not data:
            logger.warning("[ROUTE][/sections/%s] no data returned — 404", section_slug)
            abort(404)

        item_count = len(data.get("products") or data.get("contents") or [])
        log_route_success(
            logger,
            f"/sections/{section_slug}",
            products=item_count,
            template="catalog-page.html",
        )
        return render_template(
            "content/catalog/catalog-page.html",
            target_type="content",
            active_filters=active_filters,
            **data,
        )
    except Exception as e:
        log_route_error(logger, f"/sections/{section_slug}", e)
        raise


@bp.route("/sources/<source_slug>")
def source_page(source_slug):
    page = request.args.get("page", 1, type=int)
    log_route_start(logger, f"/sources/{source_slug}", page=page)
    try:
        data = get_source_feed_data(source_slug, page=page)
        if not data:
            logger.warning("[ROUTE][/sources/%s] no data returned — 404", source_slug)
            abort(404)

        item_count = len(data.get("contents") or [])
        log_route_success(
            logger,
            f"/sources/{source_slug}",
            products=item_count,
            template="catalog-page.html",
        )
        return render_template(
            "content/catalog/catalog-page.html",
            target_type="content",
            active_filters={"source": [source_slug]},
            section={"name": data["source"].get("name", "Source"), "slug": "sources"},
            **data,
        )
    except Exception as e:
        log_route_error(logger, f"/sources/{source_slug}", e)
        raise


@bp.route("/api/globe-data")
def globe_data():
    """Returns geographical data for the 3D globe visualization."""
    return jsonify(get_globe_data_workflow())


@bp.route("/contents/<content_slug>")
def content_page(content_slug):
    content_id = int(content_slug.split('-')[0])
    log_route_start(logger, f"/contents/{content_id}")

    user = current_user if current_user.is_authenticated else None
    ip_address = None if user else get_client_ip()

    try:
        data = get_content_page_data(content_id)
        if not data:
            logger.warning("[ROUTE][/contents/%d] no data returned — 404", content_id)
            abort(404)
        record_content_view(content_id, user, ip_address)
        log_route_success(logger, f"/contents/{content_id}", template="page.html")
        return render_template("content/dispatcher/page.html", **data)
    except Exception as e:
        log_route_error(logger, f"/contents/{content_id}", e)
        raise
