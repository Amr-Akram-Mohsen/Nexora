from flask import request

def parse_active_filters(list_names=None, scalar_names=None):
    """
    Parses active filters from request arguments.
    
    Args:
        list_names (list): List of parameter names that should be extracted as lists (e.g., category).
        scalar_names (list): List of parameter names that should be extracted as single values.
    
    Returns:
        dict: A dictionary of active filters.
    """
    filters = {}
    
    if list_names:
        for name in list_names:
            filters[name] = [f for f in request.args.getlist(name) if f.strip()]
            
    if scalar_names:
        for name in scalar_names:
            val = request.args.get(name)
            if val and val.strip():
                filters[name] = val.strip()
    
    filters['sort'] = request.args.get('sort', 'newest')
    return filters
