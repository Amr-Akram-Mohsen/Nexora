import logging
from flask import Blueprint, request, jsonify, render_template
from app.application.recommendation.search import search_workflow
from app.shared.request import get_country
from app.shared.utils.logging import log_route_start, log_route_success, log_route_error

logger = logging.getLogger(__name__)

bp = Blueprint("recommendation", __name__)

@bp.route('/search', methods=['POST', 'GET'])
def search():
    if request.method == 'POST':
        q = (request.form.get('query') or '').strip()
    else:
        q = (request.args.get('query') or '').strip()

    log_route_start(logger, "/search", query=q or "(empty)")

    try:
        search_results = search_workflow(q)
        if not isinstance(search_results, list):
            logger.warning("[ROUTE][/search] search_workflow returned non-list for query=%s", q)
            search_results = []

        log_route_success(logger, "/search", items=len(search_results), template="search-results.html")

        return jsonify({
            'success': True,
            'html': render_template(
                'search-results.html',
                search_results=search_results,
                query=q,
                country=get_country()
            )
        })
    except Exception as e:
        log_route_error(logger, "/search", e)
        return jsonify({'success': False, 'error': 'Search failed. Please try again.'}), 500
