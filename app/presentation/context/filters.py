from flask import request, url_for

def _build_url_with_args(**new_args):
    """Internal helper to merge request args and view args for URL generation."""
    args = request.args.to_dict(flat=False)
    for k, v in new_args.items():
        if v is None:
            args.pop(k, None)
        else:
            args[k] = v if isinstance(v, list) else [v]
            
    if request.view_args:
        for k, v in request.view_args.items():
            args[k] = v
    return url_for(request.endpoint, **args)

def get_filter_url(name, value, multi=True):
    args = request.args.to_dict(flat=False)
    new_val = None
    
    if multi:
        current_vals = args.get(name, [])
        if value in current_vals:
            current_vals.remove(value)
            new_val = current_vals if current_vals else None
        else:
            new_val = current_vals + [value]
    else:
        new_val = None if request.args.get(name) == value else value
            
    return _build_url_with_args(**{name: new_val, 'page': None})

def get_sort_url(sort_val):
    return _build_url_with_args(sort=sort_val)

def get_page_url(page_num):
    return _build_url_with_args(page=str(page_num))
