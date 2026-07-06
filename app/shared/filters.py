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

def format_datetime(value, format_str="%b %d, %Y %H:%M"):
    """Format an ISO-8601 date string or datetime object with time."""
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

def intcomma(value):
    """Format an integer with commas (e.g. 1000 -> 1,000)."""
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value

def duration_min(seconds):
    """Format seconds into MM:SS."""
    try:
        s = int(seconds)
        return f"{s // 60}:{s % 60:02d}"
    except (ValueError, TypeError):
        return seconds
