class TargetType:
    CONTENT = "content"
    ARTICLE = "article"
    VIDEO = "video"
    POST = "post"
    PRODUCT = "product"
    TECHNOLOGY = "technology"
    PERFUMES = "perfumes"
    ACCESSORIES = "accessories"


class YouTubeQuota:
    """YouTube Data API v3 quota accounting."""

    UNITS_PER_SEARCH: int = 100  # cost of one search.list call
    DAILY_BUDGET: int = 10_000
    RUN_BUDGET: int = 1000
