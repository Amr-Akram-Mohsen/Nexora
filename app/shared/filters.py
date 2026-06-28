import datetime
import dateutil.parser

def format_date(value, format_str="%b %d"):
    """
    Format an ISO-8601 date string or datetime object for Jinja templates.
    Fallback to 'Recent' if value is None.
    """
    if not value:
        return "Recent"
        
    if isinstance(value, str):
        try:
            dt = dateutil.parser.isoparse(value)
        except (ValueError, TypeError):
            return value
    elif isinstance(value, datetime.datetime):
        dt = value
    else:
        return value
        
    return dt.strftime(format_str)
