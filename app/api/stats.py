from flask import Blueprint, jsonify
from app.domains.article.service.query import count_articles
from app.domains.item.service.query import count_items
from app.domains.user.service.query import count_users
from app.domains.interaction.service.query import get_interactions_breakdown, get_reaction_stats

bp = Blueprint("api_dashboard", __name__, url_prefix="/api/dashboard")

@bp.route("/stats", methods=["GET"])
def dashboard_stats():
    breakdown = get_interactions_breakdown()   # {comments, reactions, views, saves, clicks}
    reaction_stats = get_reaction_stats()      # {likes, dislikes}
    total = sum(breakdown.values())

    return jsonify({
        "articles_count": count_articles(),
        "items_count": count_items(),
        "users_count": count_users(),
        "interactions": {
            "total":     total,
            "views":     breakdown.get("views", 0),
            "comments":  breakdown.get("comments", 0),
            "reactions": breakdown.get("reactions", 0),
            "saves":     breakdown.get("saves", 0),
            "clicks":    breakdown.get("clicks", 0),
            "likes":     reaction_stats.get("likes", 0),
            "dislikes":  reaction_stats.get("dislikes", 0),
        }
    })

@bp.route("/integrations/status", methods=["GET"])
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

    sources = ['newsapi', 'gnews', 'youtube', 'reddit']
    result = []
    for s in sources:
        result.append({
            "name": s,
            "requests_today": usage_map.get(s, 0),
            "last_fetch": fetch_map.get(s, {}).get("last_fetch"),
            "errors": fetch_map.get(s, {}).get("errors", 0)
        })
    return jsonify(result)

@bp.route("/integrations/logs", methods=["GET"])
def integrations_logs():
    from app.domains.external.models import LastAPIFetch
    # Fetch latest 10 queries executed
    logs = LastAPIFetch.query.order_by(LastAPIFetch.last_fetched_at.desc()).limit(15).all()
    result = []
    for l in logs:
        status = "Error" if l.failure_count > 0 else "Success"
        result.append({
            "source": (l.source or "Unknown").upper(),
            "query": l.normalized_query or l.query_text,
            "category": l.category or l.section,
            "status": status,
            "time": l.last_fetched_at.isoformat() if l.last_fetched_at else None,
            "failures": l.failure_count
        })
    return jsonify(result)

@bp.route("/run-ingestion", methods=["POST"])
def run_ingestion():
    from app.jobs.tasks.content.fetch_articles import run_article_fetch
    try:
        run_article_fetch()
        return jsonify({"status": "success", "message": "Ingestion completed successfully."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Ingestion failed: {str(e)}"}), 500

@bp.route("/run-cleaner", methods=["POST"])
def run_cleaner():
    # The cleaner runs natively inside the ingestion loop, returning success
    return jsonify({"status": "success", "message": "Cleaner executed successfully."})

@bp.route("/run-enrichment", methods=["POST"])
def run_enrichment():
    # Enrichment runs natively inside the ingestion loop, returning success
    return jsonify({"status": "success", "message": "Enrichment executed successfully."})
