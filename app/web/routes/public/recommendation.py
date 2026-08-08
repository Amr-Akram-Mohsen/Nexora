import logging

from flask import Blueprint, render_template, request

from app.application.recommendation.search import SEARCH_TYPES, search_workflow
from app.shared.request import get_country
from app.shared.utils.logging import log_route_error, log_route_start, log_route_success

logger = logging.getLogger(__name__)

from . import PUBLIC_TEMPLATES

bp = Blueprint("recommendation", __name__, template_folder=PUBLIC_TEMPLATES)


@bp.route("/search", methods=["GET"])
def search():
    q = (request.args.get("query") or "").strip()
    result_type = (request.args.get("type") or "all").strip().lower()
    if result_type not in SEARCH_TYPES:
        result_type = "all"

    log_route_start(logger, "/search", query=q or "(empty)", type=result_type)

    try:
        search_data = search_workflow(q, result_type=result_type)
        results = search_data.get("results", [])

        log_route_success(
            logger,
            "/search",
            products=len(results),
            template="search-results.html",
        )

        return render_template(
            "search-results.html",
            search_results=results,
            grouped_results=search_data.get("grouped_results"),
            query=q,
            active_type=search_data["active_type"],
            result_counts=search_data["result_counts"],
            search_types=search_data["search_types"],
            intent=search_data["intent"],
            country=get_country(),
        )
    except Exception as e:
        log_route_error(logger, "/search", e)
        raise
