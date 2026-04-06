# app/services/api_service.py
"""
API rate-limit tracking and fetch-cooldown guard.
Used by NewsAPI, GNews, and YouTube scrapers before making requests.
"""
import logging
from datetime import date, datetime, timedelta

from app.models import db
from app.api_models import LastAPIFetch, APIUsage

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

def should_refetch(section: str, query_text: str, hours: int = 6) -> bool:
    """
    Returns True if we haven't fetched this section+query combination
    in the past `hours` hours.
    """
    rec = LastAPIFetch.query.filter_by(
        section=section, query_text=query_text
    ).first()
    if not rec:
        return True
    return datetime.utcnow() - rec.last_fetched_at > timedelta(hours=hours)


def mark_fetched(section: str, query_text: str):
    rec = LastAPIFetch.query.filter_by(
        section=section, query_text=query_text
    ).first()
    if rec:
        rec.last_fetched_at = datetime.utcnow()
    else:
        db.session.add(LastAPIFetch(
            section=section,
            query_text=query_text,
            last_fetched_at=datetime.utcnow(),
        ))
    db.session.commit()
