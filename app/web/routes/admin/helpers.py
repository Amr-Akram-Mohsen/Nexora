# app/admin/helpers.py
"""
Shared admin utilities: pagination envelopes, param parsing, and sort helpers.
"""
from flask import request
from app.core.decorators import admin_required

# ──────────────────────────────────────────────
# GUARDS
# ──────────────────────────────────────────────

def apply_admin_guard(bp):
    """
    Apply the @admin_required guard to all routes in a blueprint via before_request.
    """
    @bp.before_request
    @admin_required
    def require_admin():
        pass


# ──────────────────────────────────────────────
# PAGINATION
# ──────────────────────────────────────────────

def paginate_response(pagination, items_key: str = "items") -> dict:
    """
    Build a consistent pagination envelope from a SQLAlchemy Pagination object.

    Args:
        pagination: A Flask-SQLAlchemy Pagination object.
        items_key:  The key name to use for the items list in the response.

    Returns:
        A dict with {items_key, page, pages, total, per_page}.
    """
    return {
        items_key: pagination.items,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "per_page": pagination.per_page,
    }


def paginate_manual(items: list, page: int, per_page: int, total: int) -> dict:
    """
    Build a consistent pagination envelope for manually paginated results
    (e.g., raw table queries that don't use SQLAlchemy Pagination).

    Args:
        items:    The current page of serialized items.
        page:     Current page number (1-indexed).
        per_page: Number of items per page.
        total:    Total count of all matching records.

    Returns:
        A dict with {items, page, pages, total, per_page}.
    """
    pages = max(1, (total + per_page - 1) // per_page)
    return {
        "items": items,
        "page": page,
        "pages": pages,
        "total": total,
        "per_page": per_page,
    }


# ──────────────────────────────────────────────
# QUERY PARAM PARSING
# ──────────────────────────────────────────────

def parse_pagination_params(default_per_page: int = 20) -> tuple[int, int]:
    """
    Parse `page` and `per_page` from the current request's query string.

    Returns:
        (page, per_page) tuple, both guaranteed to be positive integers.
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", default_per_page, type=int)
    page = max(1, page)
    per_page = max(1, min(per_page, 200))  # cap at 200 to prevent abuse
    return page, per_page


def parse_sort_params(col_map: dict, default_col, default_dir: str = "desc"):
    """
    Parse `sort_by` and `sort_dir` from the current request's query string.
    Only allows columns that appear in `col_map` (safe allowlist).

    Args:
        col_map:     Dict mapping sort key strings to ORM column expressions.
        default_col: The ORM column to use when sort_by is absent/invalid.
        default_dir: The default sort direction ("asc" or "desc").

    Returns:
        (sort_column, sort_direction_str) tuple ready to pass to .order_by().
    """
    sort_by = request.args.get("sort_by", "")
    sort_dir = request.args.get("sort_dir", default_dir).lower()
    sort_col = col_map.get(sort_by, default_col)
    if sort_dir not in ("asc", "desc"):
        sort_dir = default_dir
    return sort_col, sort_dir


# ──────────────────────────────────────────────
# HTML PARTIAL RESPONSES
# ──────────────────────────────────────────────

def make_rows_response(html: str, *, total: int, pages: int, page: int):
    """
    Wrap an HTML partial in a Flask Response with the three standard
    pagination headers consumed by AdminListController on the frontend.

    Args:
        html:  Rendered HTML string to send as the response body.
        total: Total number of matching records (for X-Total header).
        pages: Total number of pages (for X-Pages header).
        page:  Current page number (for X-Page header).

    Returns:
        A Flask Response object ready to be returned from a view.
    """
    from flask import make_response as _make_response
    resp = _make_response(html)
    resp.headers["X-Total"] = total
    resp.headers["X-Pages"] = pages
    resp.headers["X-Page"]  = page
    return resp


def render_admin_rows_response(items: list, domain_type: str, *, total: int, pages: int, page: int, hide_action_column: bool = False, **kwargs):
    """
    Renders the standard _rows.html partial and wraps it in a paginated Response.
    
    Args:
        items: List of serialized dictionaries ready for the template.
        domain_type: The string representing the domain (e.g. 'user', 'comment').
        total: Total number of records matching the query.
        pages: Total number of pages available.
        page: Current page number.
        hide_action_column: Optional boolean to hide the action column in the table.
        kwargs: Additional arguments to pass to render_template.
    """
    from flask import render_template
    html = render_template(
        "admin/components/_rows.html", 
        items=items, 
        domain_type=domain_type, 
        hide_action_column=hide_action_column,
        **kwargs
    )
    return make_rows_response(html, total=total, pages=pages, page=page)


# ──────────────────────────────────────────────
# FIELD FORMATTERS
# ──────────────────────────────────────────────
# Canonical implementations live in app.shared.utils.format so that domain
# services and serializers can import them without a dependency on app.web.
# These re-exports exist for backward compatibility with existing web-layer
# imports from this module.
from app.shared.utils.format import (  # noqa: F401
    format_date,
    format_datetime,
    format_status,
    format_featured,
)

