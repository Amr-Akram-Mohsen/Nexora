"""
app/shared/utils/format.py
Shared field formatters for dates, statuses, and flags.

These are pure functions with no dependencies on any framework layer.
They can be imported by domain services, serializers, and the web layer alike.
"""


from datetime import datetime

def _parse_if_string(dt):
    if isinstance(dt, str):
        try:
            return datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            try:
                if len(dt) > 10:
                    return datetime.strptime(dt, "%Y-%m-%d %H:%M")
                return datetime.strptime(dt, "%Y-%m-%d")
            except ValueError:
                pass
    return dt

def format_date(dt, default="—", fmt="%Y-%m-%d"):
    """Format a date or datetime object to a date string.

    Args:
        dt:      The datetime (or date) object to format.  May be ``None``.
        default: Value returned when ``dt`` is falsy.
        fmt:     strftime format string.

    Returns:
        A formatted string, or ``default`` when ``dt`` is ``None``.
    """
    if not dt:
        return default
    dt = _parse_if_string(dt)
    return dt.strftime(fmt) if hasattr(dt, "strftime") else str(dt)


def format_datetime(dt, default="—", fmt="%Y-%m-%d %H:%M"):
    """Format a datetime object to a date-and-time string.

    Args:
        dt:      The datetime object to format.  May be ``None``.
        default: Value returned when ``dt`` is falsy.
        fmt:     strftime format string.

    Returns:
        A formatted string, or ``default`` when ``dt`` is ``None``.
    """
    if not dt:
        return default
    dt = _parse_if_string(dt)
    return dt.strftime(fmt) if hasattr(dt, "strftime") else str(dt)


def format_status(is_active: bool) -> str:
    """Format a boolean active flag to a human-readable status label.

    Returns:
        ``"active"`` when *is_active* is truthy, ``"inactive"`` otherwise.
    """
    return "active" if is_active else "inactive"


def format_featured(is_featured: bool) -> str:
    """Format a boolean featured flag to a human-readable label.

    Returns:
        ``"featured"`` when *is_featured* is truthy, ``"standard"`` otherwise.
    """
    return "featured" if is_featured else "standard"
