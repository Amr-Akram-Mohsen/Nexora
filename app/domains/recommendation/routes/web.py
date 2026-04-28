from . import bp

from random import shuffle
from flask import request, jsonify, render_template
from app.domains.item.service import get_search_items
from app.domains.content.service import get_search_contents
from app.shared.request import get_country

# ============== SEARCH LOGIC ================
@bp.route('/search', methods=['POST', 'GET'])
def search():
    if request.method == 'POST':
        q = (request.form.get('query') or '').strip()
    else:
        q = (request.args.get('query') or '').strip()

    items = get_search_items(q)
    contents = get_search_contents(q)    

    search_results = contents + items
    shuffle(search_results)

    return jsonify({
        'success': True,
        'html': render_template(
            'search-results.html',
            search_results=search_results,
            query=q,
            country=get_country()
        )
    })

