import logging
from flask import Blueprint, request, render_template, abort
from app.application.content.get_feed import get_feed_data
from flask_login import current_user
from app.shared.request import get_client_ip
from app.shared.utils.logging import log_route_start, log_route_success, log_route_error

logger = logging.getLogger(__name__)

bp = Blueprint("content", __name__)


@bp.route("/sections/<section_slug>")
def sections(section_slug):
    from app.web.helpers.content import parse_active_filters

    active_filters = parse_active_filters(
        ["category", "topic", "brand", "intent", "price_tier", "type", "attributes"]
    )
    page = request.args.get("page", 1, type=int)

    log_route_start(
        logger, f"/sections/{section_slug}", page=page, filters=active_filters
    )

    try:
        data = get_feed_data(section_slug, active_filters, page=page)
        if not data:
            logger.warning("[ROUTE][/sections/%s] no data returned — 404", section_slug)
            abort(404)

        # Safety defaults before template render
        data.setdefault("items", [])
        data.setdefault("pagination", None)
        data.setdefault("section", None)
        data.setdefault("trending_contents", [])

        item_count = len(data.get("items") or [])
        log_route_success(
            logger,
            f"/sections/{section_slug}",
            items=item_count,
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


@bp.route("/contents/<int:content_id>")
def content_page(content_id):
    from app.application.content.get_content_page import (
        record_content_view,
        get_content_page_data,
    )
    from app.core.extensions import db

    log_route_start(logger, f"/contents/{content_id}")

    user = current_user if current_user.is_authenticated else None
    ip_address = None if user else get_client_ip()

    try:
        data = get_content_page_data(content_id)
        if not data:
            logger.warning("[ROUTE][/contents/%d] no data returned — 404", content_id)
            abort(404)

        # Safety defaults
        data.setdefault("content", None)
        data.setdefault("related_contents", [])
        data.setdefault("trending_contents", [])
        data.setdefault("matched_items", [])

        record_content_view(content_id, user, ip_address)
        db.session.commit()

        log_route_success(logger, f"/contents/{content_id}", template="page.html")

        return render_template("content/dispatcher/page.html", **data)

    except Exception as e:
        log_route_error(logger, f"/contents/{content_id}", e)
        raise
