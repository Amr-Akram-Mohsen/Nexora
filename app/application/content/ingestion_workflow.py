import logging
import random
from typing import Callable, List, Dict, Optional
from flask import current_app
from .ingestion.ports import DiscoveryPort, FetcherPort, EnrichmentPort, QuotaPort, CooldownPort, ClassificationPort
from .ingestion import ingest_content
from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError

logger = logging.getLogger(__name__)

class IngestionWorkflow:
    """
    Centralized workflow for content ingestion.
    """

    def __init__(
        self, 
        source_name: str, 
        discovery: DiscoveryPort,
        quota_service: QuotaPort,
        enrichment_service: EnrichmentPort,
        cooldown_service: CooldownPort,
        classification_service: ClassificationPort
    ):
        self.source_name = source_name
        self.discovery = discovery
        self.quota_service = quota_service
        self.enrichment_service = enrichment_service
        self.cooldown_service = cooldown_service
        self.classification_service = classification_service

    def run(
        self, 
        session,
        object_type: str, 
        source_filter: str, 
        fetcher: FetcherPort,
        limit: Optional[int] = None, 
        **fetch_params
    ) -> int:
        """
        Executes the ingestion workflow.
        """
        total_stored = 0
        queries_registry = self.discovery.get_queries_by_section(source_filter=source_filter)
        
        flat_tasks = []
        for section, categories in queries_registry.items():
            for category, queries in categories.items():
                for q in queries:
                    flat_tasks.append((section, category, q))

        if not flat_tasks:
            logger.info(f"[{self.source_name}] No queries found for filter: {source_filter}")
            return 0

        if limit:
            random.shuffle(flat_tasks)
            flat_tasks = flat_tasks[:limit]

        logger.info(f"[{self.source_name}] Starting ingestion workflow with {len(flat_tasks)} tasks")

        for section, category, q_obj in flat_tasks:
            try:
                q_text = q_obj["query"]
                cache_key = f"{source_filter}:{category}:{q_text}"
                
                # 1. Cooldown Check
                cooldown_hrs = fetch_params.get("cooldown_hours", 6)
                if not self.cooldown_service.should_refetch(section, cache_key, hours=cooldown_hrs):
                    continue

                if not self.quota_service.can_call():
                    logger.warning(f"[{self.source_name}] Quota exceeded — stopping")
                    break

                logger.info("[%s] fetching query: %s", self.source_name, q_text)
                
                # 2. Filter fetch_params
                sanitized_params = {k: v for k, v in fetch_params.items() if k != "cooldown_hours"}
                
                raw_items = fetcher(q_obj, **sanitized_params)
                self.quota_service.record_call()
                self.cooldown_service.mark_fetched(section, cache_key, category=category, source=source_filter, normalized_query=q_text)

                query_stored = 0
                for raw in raw_items:
                    item_title = getattr(raw, 'title', None)
                    if not item_title and hasattr(raw, 'get'):
                        item_title = raw.get('title', 'Unknown Title')
                    item_title = str(item_title)[:50] if item_title else 'Unknown Title'
                    
                    logger.debug("[%s] processing item: %s", self.source_name, item_title)

                    # Backward compatibility hook: Convert DTO back to dict for the legacy pipeline
                    if hasattr(raw, "model_dump"):
                        raw = raw.model_dump()
                    elif hasattr(raw, "dict"):
                        raw = raw.dict()

                    # 3. Metadata Classification (Tags, Brands, Facets)
                    classified = self.classification_service(raw, section, category, q_obj)
                    
                    # 4. Content Enrichment (Scraping/Strategies)
                    enriched = self.enrichment_service(classified, section, category, q_obj)
                    
                    # Backward compatibility for Cleaner / Ingest pipeline
                    if hasattr(enriched, "model_dump"):
                        enriched_dict = enriched.model_dump()
                    elif hasattr(enriched, "dict"):
                        enriched_dict = enriched.dict()
                    else:
                        enriched_dict = enriched

                    # --- DEBUG LOGGING ---
                    logger.debug(f"[{self.source_name}] Preparing to ingest. Keys present: {list(enriched_dict.keys())}")
                    
                    missing_critical = []
                    # Check URL and title. external_id is only required for video/post.
                    for key in ["url", "title"]:
                        if not enriched_dict.get(key):
                            missing_critical.append(key)
                            
                    if missing_critical:
                        logger.warning(f"[{self.source_name}] WARNING: Missing critical fields {missing_critical} for item!")
                    # ---------------------

                    # 5. Ingestion (Deduplication + Persistence)
                    try:
                        result = ingest_content(session, object_type=object_type, raw_data=enriched_dict)
                        if result:
                            content_obj, is_new = result
                            if is_new:
                                query_stored += 1
                                logger.info("[%s] [NEW] %s", self.source_name, item_title)
                            else:
                                logger.info("[%s] [UPDATED] %s", self.source_name, item_title)
                        else:
                            logger.debug("[%s] [SKIP] %s (duplicate or invalid)", self.source_name, item_title)
                    except Exception as e:
                        import sqlalchemy.exc
                        if isinstance(e, (sqlalchemy.exc.OperationalError, sqlalchemy.exc.InterfaceError)):
                            logger.critical(f"[{self.source_name}] FATAL DB ERROR: {str(e)}")
                            raise PipelineFatalError(f"Database error: {str(e)}") from e
                        logger.error(f"[{self.source_name}] Skipping item due to ingestion error: {str(e)}")
                
                if query_stored > 0:
                    session.commit()
                    total_stored += query_stored
                    logger.info("[%s] stored %d new %s(s) for query: %s", self.source_name, query_stored, object_type, q_text)

            except (PipelineFatalError, PipelineQuotaExceededError):
                session.rollback()
                raise
            except Exception as e:
                session.rollback()
                import sqlalchemy.exc
                if isinstance(e, (sqlalchemy.exc.OperationalError, sqlalchemy.exc.InterfaceError)):
                    logger.error(f"[{self.source_name}] Network/DB Connection Lost during task: {q_text}. Error: {str(e)}")
                    raise PipelineFatalError(f"Database connectivity lost: {str(e)}") from e
                else:
                    logger.exception(f"[{self.source_name}] Unexpected logic error processing query: {q_text}")

        return total_stored

def run_orchestrated_ingestion(
    session,
    source_name: str,
    object_type: str,
    fetcher_func: Callable,
    quota_service: QuotaPort,
    enrichment_service: EnrichmentPort,
    discovery_service: DiscoveryPort,
    cooldown_service: CooldownPort,
    classification_service: ClassificationPort,
    source_filter: str,
    limit: Optional[int] = None,
    cooldown_hours: int = 6,
    manual_queries: Optional[List[Dict]] = None,
    **extra_params
) -> int:
    """
    Helper to run an orchestrated ingestion run using injected dependencies.
    """
    workflow = IngestionWorkflow(
        source_name=source_name,
        discovery=discovery_service,
        quota_service=quota_service,
        enrichment_service=enrichment_service,
        cooldown_service=cooldown_service,
        classification_service=classification_service
    )
    
    if manual_queries:
        class ManualDiscovery:
            def get_queries_by_section(self, source_filter):
                registry = {}
                for q in manual_queries:
                    sec = q.get("section", "news")
                    cat = q.get("category", "uncategorized")
                    registry.setdefault(sec, {}).setdefault(cat, []).append(q)
                return registry
        workflow.discovery = ManualDiscovery()

    return workflow.run(
        session=session,
        object_type=object_type,
        source_filter=source_filter,
        fetcher=fetcher_func,
        limit=limit,
        cooldown_hours=cooldown_hours,
        **extra_params
    )
