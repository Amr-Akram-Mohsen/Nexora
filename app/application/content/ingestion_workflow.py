import logging
import random
from typing import Callable, List, Dict, Optional
from flask import current_app
from .ingestion.ports import DiscoveryPort, FetcherPort, EnrichmentPort, QuotaPort, CooldownPort
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
        cooldown_service: CooldownPort
    ):
        self.source_name = source_name
        self.discovery = discovery
        self.quota_service = quota_service
        self.enrichment_service = enrichment_service
        self.cooldown_service = cooldown_service

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
                
                # 1. Cooldown Check (Moved inside try to handle transient DB blips)
                cooldown_hrs = fetch_params.get("cooldown_hours", 6)
                if not self.cooldown_service.should_refetch(section, cache_key, hours=cooldown_hrs):
                    continue

                if not self.quota_service.can_call():
                    logger.warning(f"[{self.source_name}] Quota exceeded — stopping")
                    break

                print(f"  [{self.source_name}] Fetching: {q_text}...")
                
                # 2. Filter fetch_params to avoid leaking app-level config to integrations
                sanitized_params = {k: v for k, v in fetch_params.items() if k != "cooldown_hours"}
                
                raw_items = fetcher(q_obj, **sanitized_params)
                self.quota_service.record_call()
                self.cooldown_service.mark_fetched(section, cache_key, category=category, source=source_filter, normalized_query=q_text)

                query_stored = 0
                for raw in raw_items:
                    # Enrichment (Classification + Content)
                    enriched = self.enrichment_service(raw, section, category, q_obj)
                    
                    # Ingestion (No internal commit)
                    try:
                        if ingest_content(session, object_type=object_type, raw_data=enriched):
                            query_stored += 1
                    except Exception as e:
                        logger.critical(f"[{self.source_name}] FATAL: Ingestion failed.")
                        raise PipelineFatalError(f"Database error: {str(e)}") from e
                
                # Transaction Boundary: Commit after each discovery query
                if query_stored > 0:
                    session.commit()
                    total_stored += query_stored
                    print(f"    -> Stored {query_stored} new {object_type}s")

            except (PipelineFatalError, PipelineQuotaExceededError):
                session.rollback()
                raise
            except Exception as e:
                session.rollback()
                # Special handling for transient DB connection issues
                import sqlalchemy.exc
                if isinstance(e, sqlalchemy.exc.OperationalError):
                    logger.error(f"[{self.source_name}] DB Connectivity issue (OperationalError). Skipping task: {q_text}")
                else:
                    logger.exception(f"[{self.source_name}] Unexpected error processing query: {q_text}")

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
        cooldown_service=cooldown_service
    )
    
    # Handle manual queries if provided
    if manual_queries:
        # Custom Discovery implementation for manual queries
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
