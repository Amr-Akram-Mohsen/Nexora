class TargetType:
    CONTENT = "content"
    ARTICLE = "article"
    VIDEO = "video"
    POST = "post"
    ITEM = "item"


class FetchLimits:
    """
    Default per-run query limits for each fetch command.

    These caps control how many queries are processed in a single
    execution, spreading taxonomy coverage across multiple runs instead
    of exhausting the full query universe at once.

    Override at call-site when a larger or smaller batch is needed.
    """
    # ── Article sources ───────────────────────────────────────────────
    NEWSAPI: int = 10         # 5 × ~4 runs/day = 20 calls  (quota: 100)
    GNEWS:   int = 3         # 3 × ~4 runs/day = 12 calls  (quota: 100 — keep conservative)
    RSS:     int = 25        # No hard quota

    # ── Video source ─────────────────────────────────────────────────
    YOUTUBE: int = 10         # 8 × 100 units × 4 runs = 3,200 units  (budget: 10,000)

    # ── Social source ─────────────────────────────────────────────────
    REDDIT:  int = 20        # No hard quota


class CooldownHours:
    """
    Centralised cooldown windows that reflect how often each source
    actually publishes new content.

    - RSS      : 0.5 h — feeds refresh every 15–60 min; ETag prevents wasted calls
    - NewsAPI  : 6 h  — news cycles are 6–12 h; free tier has 100 calls/day
    - GNews    : 8 h  — was 24 h (too conservative); news goes stale in 6–12 h
    - YouTube (reviews/tutorials): 24 h — review videos are stable, not hourly
    - YouTube (trends): 12 h — trend queries need more frequent refreshes
    - Reddit   : 4 h  — community threads update rapidly
    """
    RSS:             float = 0.5
    NEWSAPI:         float = 6.0
    GNEWS:           float = 8.0
    YOUTUBE_REVIEWS: float = 24.0
    YOUTUBE_TRENDS:  float = 12.0
    REDDIT:          float = 4.0


class YouTubeQuota:
    """YouTube Data API v3 quota accounting."""
    UNITS_PER_SEARCH: int = 100   # cost of one search.list call
    DAILY_BUDGET:     int = 10_000
    RUN_BUDGET:       int = 800   # 8 searches × 100 units; raised from 500
