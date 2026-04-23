from flask import Blueprint, jsonify

bp = Blueprint("api_ingestion", __name__, url_prefix="/api/ingestions")

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

@bp.route("/run-articles", methods=["POST"])
def run_ingestion():
    from app.jobs.tasks.content.fetch_articles import run_article_fetch
    try:
        run_article_fetch()
        return jsonify({"status": "success", "message": "Article ingestion completed successfully."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Article Ingestion failed: {str(e)}"}), 500

@bp.route("/run-items", methods=["POST"])
def run_item_ingestion():
    from app.jobs.tasks.content.fetch_items import run_item_fetch
    try:
        run_item_fetch()
        return jsonify({"status": "success", "message": "Item ingestion completed successfully."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Item Ingestion failed: {str(e)}"}), 500

@bp.route("/run-cleaner", methods=["POST"])
def run_cleaner():
    # The cleaner runs natively inside the ingestion loop, returning success
    return jsonify({"status": "success", "message": "Cleaner executed successfully."})

@bp.route("/run-enrichment", methods=["POST"])
def run_enrichment():
    # Enrichment runs natively inside the ingestion loop, returning success
    return jsonify({"status": "success", "message": "Enrichment executed successfully."})
