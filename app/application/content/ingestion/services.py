from .ports import DiscoveryPort, QuotaPort, EnrichmentPort, CooldownPort, ClassificationPort
from app.integrations.discovery import DiscoveryManager
from app.integrations.enrichment.classification import classify_content_metadata

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
    def __init__(self, should_scrape: bool = False):
        self.should_scrape = should_scrape

    def __call__(self, raw_data, section, category, query_obj):
        from app.integrations.enrichment.pipeline import route_enrichment_strategy
        return route_enrichment_strategy(raw_data, should_scrape=self.should_scrape)

class CooldownService(CooldownPort):
    def should_refetch(self, section, cache_key, hours):
        from app.integrations.external.api import should_refetch
        return should_refetch(section, cache_key, hours=hours)

    def mark_fetched(self, section, cache_key, category, source, normalized_query):
        from app.integrations.external.api import mark_fetched
        mark_fetched(section, cache_key, category=category, source=source, normalized_query=normalized_query)

class NewsApiQuotaService(QuotaPort):
# ... existing classes ...
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
    def can_call(self):
        from app.integrations.external.api import can_call_youtube
        return can_call_youtube(units=100)

    def record_call(self):
        from app.integrations.external.api import record_youtube_call
        record_youtube_call(units=100)

class GenericQuotaService(QuotaPort):
    """Fallback quota service that always allows."""
    def can_call(self): return True
    def record_call(self): pass
