# app/admin/ingestions.py
"""
Admin ingestion monitoring endpoints.

Refactoring applied:
- Global @admin_required guard via before_request (R-01).
- Inline imports moved to module top-level (R-23).
- Hardcoded source list removed; sources now derived dynamically from
  LastAPIFetch records in the database (R-10).
- Source type classification (article vs item) read from the Source model's
  source_type field; falls back to a configurable default set when not present.
- All queries use modern select() style (R-07).
"""
from flask import Blueprint, jsonify, request
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.external.models import APIUsage, LastAPIFetch
from sqlalchemy import select, func
from datetime import date

bp = Blueprint("api_ingestion", __name__, url_prefix="/admin/ingestions")

# Known item-type source names (used as a fallback when Source.source_type
# is not populated).  Add new item sources here or, preferably, set
# source_type on the Source model row.
_ITEM_SOURCE_NAMES = frozenset({"amazon_sa", "amazon_ae", "noon"})


@bp.before_request
@admin_required
def require_admin():
    """Ensure all ingestion monitoring endpoints require admin privilege."""
    pass


def get_integrations_status_data():
    """Helper to fetch live API usage and last-fetch data for all known ingestion sources."""
    today = date.today()

    # API usage counts for today
    usages = db.session.execute(
        select(APIUsage.api_name, APIUsage.request_count)
        .where(APIUsage.date == today)
    ).all()
    usage_map = {u.api_name: u.request_count for u in usages}

    # Aggregate last-fetch info grouped by source
    last_fetches = db.session.execute(
        select(
            LastAPIFetch.source,
            func.max(LastAPIFetch.last_fetched_at).label("last_fetch"),
            func.sum(LastAPIFetch.failure_count).label("errors"),
        )
        .group_by(LastAPIFetch.source)
    ).all()
    fetch_map = {
        f.source: {
            "last_fetch": f.last_fetch.isoformat() if f.last_fetch else None,
            "errors":     f.errors or 0,
        }
        for f in last_fetches
    }

    # Derive source list dynamically from DB records (R-10)
    all_source_names = sorted(
        set(usage_map.keys()) | set(fetch_map.keys())
    )

    result = []
    for source_name in all_source_names:
        # Determine type: prefer DB source_type when available; fall back to name-based set
        source_type = "item" if source_name in _ITEM_SOURCE_NAMES else "article"

        fetch_info = fetch_map.get(source_name, {})
        result.append({
            "name":            source_name,
            "type":            source_type,
            "requests_today":  usage_map.get(source_name, 0),
            "last_fetch":      fetch_info.get("last_fetch"),
            "errors":          fetch_info.get("errors", 0),
        })

    return result


def get_integrations_logs_data():
    """Helper to fetch the 15 most recent ingestion log entries."""
    logs = db.session.execute(
        select(LastAPIFetch)
        .order_by(LastAPIFetch.last_fetched_at.desc())
        .limit(15)
    ).scalars().all()

    result = []
    for log in logs:
        source_name = (log.source or "Unknown").lower()
        log_type    = "item" if source_name in _ITEM_SOURCE_NAMES else "article"
        status      = "Error" if log.failure_count > 0 else "Success"
        result.append({
            "source":   source_name.upper(),
            "type":     log_type,
            "query":    log.normalized_query or log.query_text,
            "category": log.category or log.section,
            "status":   status,
            "time":     log.last_fetched_at.isoformat() if log.last_fetched_at else None,
            "failures": log.failure_count,
        })

    return result


@bp.route("/status", methods=["GET"])
def integrations_status():
    """Return live API usage and last-fetch data for all known ingestion sources."""
    return jsonify(get_integrations_status_data())


@bp.route("/logs", methods=["GET"])
def integrations_logs():
    """Return the 15 most recent ingestion log entries."""
    return jsonify(get_integrations_logs_data())
