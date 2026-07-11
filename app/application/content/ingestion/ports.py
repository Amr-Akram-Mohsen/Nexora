from typing import Protocol, List, Dict, Optional

class DiscoveryPort(Protocol):
    def get_queries_by_section(self, source_filter: str) -> Dict[str, Dict[str, List[Dict]]]: ...

class FetcherPort(Protocol):
    def __call__(self, query_obj: Dict, **kwargs) -> List[Dict]: ...

class EnrichmentPort(Protocol):
    def __call__(self, raw_data: Dict, section: str, category: str, query_obj: Dict) -> Dict: ...

class TaxonomyEnrichmentPort(Protocol):
    """
    Post-normalization taxonomy enrichment.
    Accepts a normalized product dict and returns a dict with refined
    taxonomy assignments (category, topics, brands, facets).
    Does NOT perform scraping or network calls.
    """
    def __call__(self, enriched_data: Dict) -> Dict: ...

class ClassificationPort(Protocol):
    def __call__(self, raw_data: Dict, section: str, category: str, query_obj: Dict) -> Dict: ...

class QuotaPort(Protocol):
    def can_call(self) -> bool: ...
    def record_call(self) -> None: ...

class CooldownPort(Protocol):
    def should_refetch(self, section: str, cache_key: str, hours: int) -> bool: ...
    def get_fetch_metadata(self, section: str, cache_key: str) -> Dict: ...
    def mark_fetched(
        self,
        section: str,
        cache_key: str,
        category: str,
        source: str,
        normalized_query: str,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        had_results: bool = True,
    ) -> None: ...
    def mark_failed(self, section: str, cache_key: str, error: Exception, source: str = None) -> None: ...
