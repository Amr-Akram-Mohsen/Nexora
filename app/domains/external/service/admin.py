from sqlalchemy import select, func
from app.core.extensions import db
from app.domains.external.models import APIUsage, LastAPIFetch
from datetime import date

_ITEM_SOURCE_NAMES = frozenset({"amazon_sa", "amazon_ae", "noon"})

def get_admin_integrations_status_data():
    today = date.today()

    usages = db.session.execute(
        select(APIUsage.api_name, APIUsage.request_count)
        .where(APIUsage.date == today)
    ).all()
    usage_map = {u.api_name: u.request_count for u in usages}

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

    all_source_names = sorted(
        set(usage_map.keys()) | set(fetch_map.keys())
    )

    result = []
    for source_name in all_source_names:
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

def get_admin_integrations_logs_data():
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

def reset_admin_system_external_logs():
    db.session.execute(LastAPIFetch.__table__.delete())
    db.session.execute(APIUsage.__table__.delete())
    db.session.commit()
