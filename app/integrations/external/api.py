# app/services/api_service.py
"""
API rate-limit tracking and fetch-cooldown guard.
Used by NewsAPI, GNews, and YouTube scrapers before making requests.
"""
import logging
from datetime import date, datetime, timedelta

from app.core.extensions import db
from app.domains.external.models import LastAPIFetch, APIUsage

logger = logging.getLogger(__name__)

# ── Per-day limits for free tiers ─────────────────────────────────
NEWSAPI_DAILY_LIMIT  = 100
GNEWS_DAILY_LIMIT    = 100
YOUTUBE_DAILY_QUOTA  = 10_000   # units; 1 search = 100 units


def _get_today_usage(api_name: str) -> APIUsage | None:
    today = date.today()
    return APIUsage.query.filter_by(date=today, api_name=api_name).first()


def _today_count(api_name: str) -> int:
    rec = _get_today_usage(api_name)
    return rec.request_count if rec else 0


def _record_call(api_name: str, units: int = 1):
    today = date.today()
    rec = APIUsage.query.filter_by(date=today, api_name=api_name).first()
    if rec:
        rec.request_count += units
    else:
        db.session.add(APIUsage(date=today, request_count=units, api_name=api_name))
    db.session.commit()


# ── Public helpers — one per API ──────────────────────────────────

def can_call_newsapi() -> bool:
    return _today_count("newsapi") < NEWSAPI_DAILY_LIMIT

def record_newsapi_call():
    _record_call("newsapi")

def can_call_gnews() -> bool:
    return _today_count("gnews") < GNEWS_DAILY_LIMIT

def record_gnews_call():
    _record_call("gnews")

def can_call_youtube(units: int = 100) -> bool:
    return _today_count("youtube") + units <= YOUTUBE_DAILY_QUOTA

def record_youtube_call(units: int = 100):
    _record_call("youtube", units)


# ── Fetch-cooldown guard ──────────────────────────────────────────

FAILURE_RETRY_MINS = 15

def should_refetch(section: str, query_text: str, hours: int = 24) -> bool:
    """
    Checks if a query is on cooldown or disabled due to health issues.
    Differentiates between success (long) and failure (short) cooldowns.
    """
    rec = LastAPIFetch.query.filter_by(
        section=section, query_text=query_text
    ).first()
    
    if not rec:
        return True
    
    if not rec.is_active:
        return False

    now = datetime.utcnow()
    
    # 1. Success Cooldown (if last attempt was a success)
    is_last_success = rec.success_count > 0 and (not rec.last_failed_at or rec.last_fetched_at > rec.last_failed_at)
    
    if is_last_success:
        return now - rec.last_fetched_at > timedelta(hours=hours)
    
    # 2. Failure Cooldown (Short retry period)
    if rec.last_failed_at:
        return now - rec.last_failed_at > timedelta(minutes=FAILURE_RETRY_MINS)

    return True


def get_fetch_metadata(section: str, query_text: str) -> dict:
    """Returns stored etag/last_modified for a specific fetch task."""
    rec = LastAPIFetch.query.filter_by(section=section, query_text=query_text).first()
    if not rec:
        return {}
    return {"etag": rec.etag, "last_modified": rec.last_modified}


def mark_fetched(
    section: str, 
    query_text: str, 
    category: str = None, 
    source: str = None, 
    normalized_query: str = None,
    etag: str = None,
    last_modified: str = None
):
    """
    Updates or creates a record of a successful fetch.
    """
    rec = LastAPIFetch.query.filter_by(
        section=section, query_text=query_text
    ).first()
    
    now = datetime.utcnow()
    
    if rec:
        rec.last_fetched_at = now
        rec.success_count += 1
        rec.consecutive_failures = 0
        rec.is_active = True
        
        if category and not rec.category: rec.category = category
        if source and not rec.source: rec.source = source
        if normalized_query and not rec.normalized_query: rec.normalized_query = normalized_query
        if etag: rec.etag = etag
        if last_modified: rec.last_modified = last_modified
    else:
        db.session.add(LastAPIFetch(
            section=section,
            query_text=query_text,
            category=category,
            source=source,
            normalized_query=normalized_query,
            etag=etag,
            last_modified=last_modified,
            last_fetched_at=now,
            success_count=1,
            consecutive_failures=0,
            is_active=True
        ))
    db.session.commit()


def mark_failed(section: str, query_text: str, error: Exception, source: str = None):
    """
    Records a fetch failure and increments consecutive failure count.
    """
    rec = LastAPIFetch.query.filter_by(
        section=section, query_text=query_text
    ).first()
    
    now = datetime.utcnow()
    err_msg = str(error)[:500]
    
    if rec:
        rec.failure_count += 1
        rec.consecutive_failures += 1
        rec.last_failed_at = now
        rec.last_error = err_msg
        if source and not rec.source: rec.source = source
        
        if rec.consecutive_failures >= 5:
            rec.is_active = False
    else:
        db.session.add(LastAPIFetch(
            section=section,
            query_text=query_text,
            source=source,
            last_fetched_at=datetime(2000, 1, 1),
            failure_count=1,
            consecutive_failures=1,
            last_failed_at=now,
            last_error=err_msg,
            is_active=True
        ))
    db.session.commit()
