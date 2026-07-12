from .ports import (
    DiscoveryPort,
    QuotaPort,
    EnrichmentPort,
    TaxonomyEnrichmentPort,
    CooldownPort,
    ClassificationPort,
)
from app.integrations.content.discovery import DiscoveryManager
from app.integrations.content.enrichment.classification import classify_content_metadata
from app.shared.constants.core import YouTubeQuota
from app.integrations.content.external.api import (
    should_refetch,
    get_fetch_metadata,
    mark_fetched,
    mark_failed,
    can_call_newsapi_ai,
    record_newsapi_ai_call,
    can_call_youtube,
    record_youtube_call,
)


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


class TaxonomyEnrichmentService(TaxonomyEnrichmentPort):
    """
    Application-layer wrapper for the integration-layer taxonomy enrichment
    engine.

    Sits between normalization (EnrichmentService) and persistence so that
    taxonomy assignments are refined using full content signals before the
    product is written to the database.

    Design contract
    ---------------
    * Accepts a plain dict (the ``enriched_dict`` from the workflow).
    * Returns a plain dict with the same shape, with updated taxonomy fields.
    * Never raises — any internal failure logs a warning and returns the
      original dict unchanged, preserving backward compatibility.
    """

    def __call__(self, enriched_data: dict) -> dict:
        from app.integrations.content.enrichment.taxonomy_enrichment import (
            enrich_taxonomy,
        )
        from app.shared.dto.ingestion import EnrichedItemDTO

        try:
            dto = EnrichedItemDTO(**enriched_data)
            refined = enrich_taxonomy(dto)
            return refined.model_dump()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "[taxonomy_enrichment] failed — returning original data  err=%s", exc
            )
            return enriched_data


class EnrichmentService(EnrichmentPort):
    """
    Pure Content Enrichment (Strategy-based scraping).
    Expects data that has already been classified.

    Args:
        should_scrape: When True, enables CloudScraper/Playwright scraping for articles.
                       Defaults to False for safe, fast ingestion runs.
    """

    def __call__(self, raw_data, section, category, query_obj):
        from app.integrations.content.enrichment.pipeline import (
            ingest_enrichment_router,
        )

        # Ingestion enrichment is always lightweight (normalization only)
        return ingest_enrichment_router(raw_data)


class CooldownService(CooldownPort):
    def should_refetch(self, section, cache_key, hours):
        return should_refetch(section, cache_key, hours=hours)

    def get_fetch_metadata(self, section, cache_key):
        return get_fetch_metadata(section, cache_key)

    def mark_fetched(
        self,
        section,
        cache_key,
        category,
        source,
        normalized_query,
        etag=None,
        last_modified=None,
        had_results=True,
    ):

        mark_fetched(
            section,
            cache_key,
            category=category,
            source=source,
            normalized_query=normalized_query,
            etag=etag,
            last_modified=last_modified,
            had_results=had_results,
        )

    def mark_failed(self, section, cache_key, error, source=None):

        mark_failed(section, cache_key, error=error, source=source)


class NewsApiAiQuotaService(QuotaPort):
    def can_call(self):

        return can_call_newsapi_ai()

    def record_call(self):

        record_newsapi_ai_call()


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

        # First check the shared global quota tracker, then the run budget.
        if not can_call_youtube(units=YouTubeQuota.UNITS_PER_SEARCH):
            return False

        if self._units_used + YouTubeQuota.UNITS_PER_SEARCH > YouTubeQuota.RUN_BUDGET:
            return False

        return True

    def record_call(self) -> None:

        record_youtube_call(units=YouTubeQuota.UNITS_PER_SEARCH)
        self._units_used += YouTubeQuota.UNITS_PER_SEARCH


class GenericQuotaService(QuotaPort):
    """Fallback quota service that always allows."""

    def can_call(self):
        return True

    def record_call(self):
        pass
