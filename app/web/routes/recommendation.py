from flask import Blueprint, request, jsonify, render_template
from app.application.recommendation.search import search_workflow
from app.shared.request import get_country

bp = Blueprint("recommendation", __name__)

@bp.route('/search', methods=['POST', 'GET'])
def search():
    if request.method == 'POST':
        q = (request.form.get('query') or '').strip()
    else:
        q = (request.args.get('query') or '').strip()

    search_results = search_workflow(q)

    return jsonify({
        'success': True,
        'html': render_template(
            'search-results.html',
            search_results=search_results,
            query=q,
            country=get_country()
        )
    })
