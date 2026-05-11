from .ports import DiscoveryPort, QuotaPort, EnrichmentPort, CooldownPort, ClassificationPort
from app.integrations.discovery import DiscoveryManager
from app.integrations.enrichment.classification import classify_content_metadata
from app.shared.constants.core import YouTubeQuota


class DiscoveryService(DiscoveryPort):
    def __init__(self):
        self.manager = DiscoveryManager()

    def get_queries_by_section(self, source_filter: str):
        return self.manager.get_queries_by_section(source_filter=source_filter)


class ClassificationService(ClassificationPort):
    """
    Handles metadata tagging (Brands, Facets, Sections) for all content types.
    """
    def __call__(self, raw_data, section, category, query_obj):
        return classify_content_metadata(raw_data, section, category, query_obj)


class EnrichmentService(EnrichmentPort):
    """
    Pure Content Enrichment (Strategy-based scraping).
    Expects data that has already been classified.

    Args:
        should_scrape: When True, enables CloudScraper/Playwright scraping for articles.
                       Defaults to False for safe, fast ingestion runs.
    """
    def __call__(self, raw_data, section, category, query_obj):
        from app.integrations.enrichment.pipeline import ingest_enrichment_router
        # Ingestion enrichment is always lightweight (normalization only)
        return ingest_enrichment_router(raw_data)


class CooldownService(CooldownPort):
    def should_refetch(self, section, cache_key, hours):
        from app.integrations.external.api import should_refetch
        return should_refetch(section, cache_key, hours=hours)

    def get_fetch_metadata(self, section, cache_key):
        from app.integrations.external.api import get_fetch_metadata
        return get_fetch_metadata(section, cache_key)

    def mark_fetched(self, section, cache_key, category, source, normalized_query, etag=None, last_modified=None):
        from app.integrations.external.api import mark_fetched
        mark_fetched(
            section, cache_key, 
            category=category, 
            source=source, 
            normalized_query=normalized_query,
            etag=etag,
            last_modified=last_modified
        )

    def mark_failed(self, section, cache_key, error, source=None):
        from app.integrations.external.api import mark_failed
        mark_failed(section, cache_key, error=error, source=source)


class NewsApiQuotaService(QuotaPort):
    def can_call(self):
        from app.integrations.external.api import can_call_newsapi
        return can_call_newsapi()

    def record_call(self):
        from app.integrations.external.api import record_newsapi_call
        record_newsapi_call()


class GNewsQuotaService(QuotaPort):
    def can_call(self):
        from app.integrations.external.api import can_call_gnews
        return can_call_gnews()

    def record_call(self):
        from app.integrations.external.api import record_gnews_call
        record_gnews_call()


class YouTubeQuotaService(QuotaPort):
    """
    Tracks YouTube Data API v3 quota units within a single run.

    Each search.list call costs ``YouTubeQuota.UNITS_PER_SEARCH`` units.
    The service refuses further calls once ``YouTubeQuota.RUN_BUDGET`` units
    have been consumed, ensuring a single fetch run never exceeds ~1 000
    units (10 % of the 10 000-unit daily budget).
    """

    def __init__(self) -> None:
        self._units_used: int = 0

    def can_call(self) -> bool:
        from app.integrations.external.api import can_call_youtube
        # First check the shared global quota tracker, then the run budget.
        if not can_call_youtube(units=YouTubeQuota.UNITS_PER_SEARCH):
            return False
        remaining = YouTubeQuota.RUN_BUDGET - self._units_used
        return remaining >= YouTubeQuota.UNITS_PER_SEARCH

    def record_call(self) -> None:
        from app.integrations.external.api import record_youtube_call
        record_youtube_call(units=YouTubeQuota.UNITS_PER_SEARCH)
        self._units_used += YouTubeQuota.UNITS_PER_SEARCH


class GenericQuotaService(QuotaPort):
    """Fallback quota service that always allows."""
    def can_call(self): return True
    def record_call(self): pass
