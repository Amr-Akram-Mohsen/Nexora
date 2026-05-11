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
    NEWSAPI: int = 1         # Increased for better coverage (daily quota: 100)
    GNEWS:   int = 1         # Increased for better coverage (daily quota: 100)
    RSS:     int = 10         # Increased (no hard quota)

    # ── Video source ─────────────────────────────────────────────────
    YOUTUBE: int = 5         # 20 queries × 100 units = 2 000 units (daily budget: 10 000)

    # ── Social source ─────────────────────────────────────────────────
    REDDIT:  int = 20         # Increased (no hard quota)

class YouTubeQuota:
    """YouTube Data API v3 quota accounting."""
    UNITS_PER_SEARCH: int = 100   # cost of one search.list call
    DAILY_BUDGET:     int = 10_000
    RUN_BUDGET:       int = 500  # max units consumed in one fetch run
