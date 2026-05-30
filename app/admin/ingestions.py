from flask import Blueprint, jsonify
from app.core.decorators import admin_required

bp = Blueprint("api_ingestion", __name__, url_prefix="/admin/ingestions")


# @bp.before_request
# @admin_required
# def require_admin():
#     """Ensure all ingestion/integration endpoints require admin privilege."""
#     pass


@bp.route("/status", methods=["GET"])
def integrations_status():
    from app.domains.external.models import APIUsage, LastAPIFetch
    from app.core.extensions import db
    from sqlalchemy import func
    from datetime import date
    
    today = date.today()
    usages = APIUsage.query.filter_by(date=today).all()
    usage_map = {u.api_name: u.request_count for u in usages}

    last_fetches = db.session.query(
        LastAPIFetch.source,
        func.max(LastAPIFetch.last_fetched_at).label('last_fetch'),
        func.sum(LastAPIFetch.failure_count).label('errors')
    ).group_by(LastAPIFetch.source).all()

    fetch_map = {f.source: {'last_fetch': f.last_fetch.isoformat() if f.last_fetch else None, 'errors': f.errors} for f in last_fetches}

    sources = ['newsapi', 'gnews', 'youtube', 'reddit', 'amazon_sa', 'amazon_ae', 'noon']
    result = []
    
    item_sources = ['amazon_sa', 'amazon_ae', 'noon']
    
    for s in sources:
        result.append({
            "name": s,
            "type": "item" if s in item_sources else "article",
            "requests_today": usage_map.get(s, 0),
            "last_fetch": fetch_map.get(s, {}).get("last_fetch"),
            "errors": fetch_map.get(s, {}).get("errors", 0)
        })
    return jsonify(result)

@bp.route("/logs", methods=["GET"])
def integrations_logs():
    from app.domains.external.models import LastAPIFetch
    # Fetch latest 10 queries executed
    logs = LastAPIFetch.query.order_by(LastAPIFetch.last_fetched_at.desc()).limit(15).all()
    result = []
    for l in logs:
        source_name = (l.source or "Unknown").lower()
        log_type = "item" if source_name in ['amazon_sa', 'amazon_ae', 'noon'] else "article"
        status = "Error" if l.failure_count > 0 else "Success"
        result.append({
            "source": source_name.upper(),
            "type": log_type,
            "query": l.normalized_query or l.query_text,
            "category": l.category or l.section,
            "status": status,
            "time": l.last_fetched_at.isoformat() if l.last_fetched_at else None,
            "failures": l.failure_count
        })
    return jsonify(result)

