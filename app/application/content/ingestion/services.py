from .ports import DiscoveryPort, QuotaPort, EnrichmentPort, CooldownPort
from app.integrations.discovery import DiscoveryManager
from app.integrations.enrichment.pipeline import prepare_article, enrich_article_content

class DiscoveryService(DiscoveryPort):
    def __init__(self):
        self.manager = DiscoveryManager()

    def get_queries_by_section(self, source_filter: str):
        return self.manager.get_queries_by_section(source_filter=source_filter)

class EnrichmentService(EnrichmentPort):
    """
    Unifies classification (prepare_article) and content extraction (enrich_article_content).
    """
    def __call__(self, raw_data, section, category, query_obj):
        # 1. Classification & Tagging
        data = prepare_article(raw_data, section, category, query_obj)
        
        # 2. Content Extraction (Strategy-based)
        # Only if it's an article (videos/posts handle enrichment differently or not at all here)
        if "url" in data and not any(k in data["url"].lower() for k in ["youtube.com", "reddit.com"]):
            data = enrich_article_content(data)
            
        return data

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
