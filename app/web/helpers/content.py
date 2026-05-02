from flask import request

def parse_active_filters(filter_names):
    """
    Parses active filters from request arguments.
    """
    filters = {}
    for name in filter_names:
        filters[name] = [f for f in request.args.getlist(name) if f.strip()]
    
    filters['sort'] = request.args.get('sort', 'newest')
    return filters
