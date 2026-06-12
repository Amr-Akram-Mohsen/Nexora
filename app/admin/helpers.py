# app/admin/helpers.py
"""
Shared admin utilities: pagination envelopes, param parsing, and sort helpers.
"""
from flask import request


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
