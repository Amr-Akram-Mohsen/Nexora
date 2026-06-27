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





@bp.route("/status", methods=["GET"])
def integrations_status():
    """Return live API usage and last-fetch data for all known ingestion sources."""
    from app.domains.external.service.admin import get_admin_integrations_status_data
    return jsonify(get_admin_integrations_status_data())


@bp.route("/logs", methods=["GET"])
def integrations_logs():
    """Return the 15 most recent ingestion log entries."""
    from app.domains.external.service.admin import get_admin_integrations_logs_data
    return jsonify(get_admin_integrations_logs_data())
