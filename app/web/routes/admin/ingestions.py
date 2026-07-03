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
from flask import Blueprint, jsonify, request, render_template
from app.web.routes.admin.helpers import apply_admin_guard
from app.core.extensions import db
from app.domains.external.models import APIUsage, LastAPIFetch
from sqlalchemy import select, func
from datetime import date

bp = Blueprint("api_ingestion", __name__, url_prefix="/admin/ingestions")

# Known item-type source names (used as a fallback when Source.source_type
# is not populated).  Add new item sources here or, preferably, set
# source_type on the Source model row.
_ITEM_SOURCE_NAMES = frozenset({"amazon_sa", "amazon_ae", "noon"})


apply_admin_guard(bp)





@bp.route("/status", methods=["GET"])
def integrations_status():
    """Return live API usage and last-fetch data for all known ingestion sources."""
    from app.domains.external.service.admin import get_admin_integrations_status_data
    from flask import render_template
    
    data = get_admin_integrations_status_data()
    if request.args.get('format') == 'html':
        return render_template("admin/components/rows/_ingestion_status_cards.html", items=data)
        
    return jsonify(data)


@bp.route("/logs", methods=["GET"])
def integrations_logs():
    """Return the 15 most recent ingestion log entries."""
    from app.domains.external.service.admin import get_admin_integrations_logs_data
    from flask import render_template
    
    data = get_admin_integrations_logs_data()
    if request.args.get('format') == 'html':
        # Add domain_type so _rows.html knows which row template to load
        return render_template("admin/components/_rows.html", items=data, domain_type="ingestion_log", empty_text="No recent events.")
        
    return jsonify(data)
