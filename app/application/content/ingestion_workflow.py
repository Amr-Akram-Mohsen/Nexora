import logging
import random
from typing import Callable, List, Dict, Optional
from flask import current_app
from app.core.extensions import db
from app.integrations.discovery import DiscoveryManager
from app.integrations.external.api import (
    should_refetch, mark_fetched
)
from app.integrations.exceptions import (
    PipelineFatalError, PipelineQuotaExceededError
)
from app.domains.content.ingestion import ingest_content

logger = logging.getLogger(__name__)

class IngestionWorkflow:
    """
    Centralized workflow for content ingestion.
    Handles quota management, cooldowns, and error reporting.
    """

    def __init__(self, source_name: str, can_call_func: Callable, record_call_func: Callable):
        self.source_name = source_name
        self.can_call_func = can_call_func
        self.record_call_func = record_call_func
        self.discovery = DiscoveryManager()

    def run(self, object_type: str, source_filter: str, limit: Optional[int] = None, **fetch_params) -> int:
        """
        Executes the ingestion workflow for a given source and object type.
        """
        total_stored = 0
        queries_registry = self.discovery.get_queries_by_section(source_filter=source_filter)
        
        # Flatten queries into a single list of tasks
        flat_tasks = []
        for section, categories in queries_registry.items():
            for category, queries in categories.items():
                for q in queries:
                    flat_tasks.append({
                        "section": section,
                        "category": category,
                        "query_obj": q
                    })

        if not flat_tasks:
            logger.info(f"[{self.source_name}] No queries found for filter: {source_filter}")
            return 0

        # Diverse sampling
        if limit:
            random.shuffle(flat_tasks)
            flat_tasks = flat_tasks[:limit]

        logger.info(f"[{self.source_name}] Starting ingestion workflow with {len(flat_tasks)} tasks")

        for task in flat_tasks:
            section = task["section"]
            category = task["category"]
            q_obj = task["query_obj"]
            q_text = q_obj["query"]
            
            # 1. Cooldown Check
            cache_key = f"{source_filter}:{category}:{q_text}"
            if not should_refetch(section, cache_key, hours=fetch_params.get("cooldown_hours", 6)):
                continue

            # 2. Quota Check
            if not self.can_call_func():
                logger.warning(f"[{self.source_name}] Quota exceeded or limit reached — stopping")
                break

            try:
                print(f"  [{self.source_name}] Fetching: {q_text}...")
                
                # The actual API call is passed via fetcher_func in run_orchestrated
                # But here we assume a standardized fetcher pattern
                from app.integrations.enrichment.pipeline import prepare_article
                
                # Call the fetcher (this will be refactored into the scrapers)
                # For now, this is a placeholder for the logic we will move
                
                # 3. Execute Fetch (This logic will be in the scraper files)
                # items = self.fetcher(q_obj, **fetch_params)
                
                # 4. Record Call
                # self.record_call_func()
                
                # 5. Mark Fetched
                # mark_fetched(...)
                
                # 6. Ingest
                # for raw in items:
                #     raw = prepare_article(raw, section, category, q_obj)
                #     if ingest_content(db.session, object_type=object_type, raw_data=raw):
                #         total_stored += 1
                
                pass # Logic will be finalized as we refactor scrapers
                
            except (PipelineFatalError, PipelineQuotaExceededError):
                raise
            except Exception:
                logger.exception(f"[{self.source_name}] Unexpected error processing query: {q_text}")

        return total_stored

def run_orchestrated_ingestion(
    source_name: str,
    object_type: str,
    fetcher_func: Callable,
    can_call_func: Callable,
    record_call_func: Callable,
    source_filter: str,
    limit: Optional[int] = None,
    cooldown_hours: int = 6,
    manual_queries: Optional[List[Dict]] = None,
    **extra_params
) -> int:
    """
    Helper to run an orchestrated ingestion run.
    """
    total_stored = 0
    
    flat_tasks = []
    if manual_queries:
        for q in manual_queries:
            flat_tasks.append((q.get("section", "news"), q.get("category", "uncategorized"), q))
    else:
        discovery = DiscoveryManager()
        queries_registry = discovery.get_queries_by_section(source_filter=source_filter)
        for section, categories in queries_registry.items():
            for category, queries in categories.items():
                for q in queries:
                    flat_tasks.append((section, category, q))

    if limit:
        random.shuffle(flat_tasks)
        flat_tasks = flat_tasks[:limit]

    logger.info(f"[{source_name}] Orchestrating run with {len(flat_tasks)} queries")

    for section, category, q_obj in flat_tasks:
        q_text = q_obj["query"]
        cache_key = f"{source_filter}:{category}:{q_text}"
        
        if not should_refetch(section, cache_key, hours=cooldown_hours):
            continue

        if not can_call_func():
            logger.warning(f"[{source_name}] Limit reached")
            break

        try:
            print(f"  [{source_name}] {q_text}...")
            
            # Fetch raw data
            raw_items = fetcher_func(q_obj, **extra_params)
            
            # Tracking
            record_call_func()
            mark_fetched(section, cache_key, category=category, source=source_filter, normalized_query=q_text)
            
            from app.integrations.enrichment.pipeline import prepare_article
            
            query_stored = 0
            for raw in raw_items:
                # Enrichment
                raw = prepare_article(raw, section, category, q_obj)
                
                # Ingestion
                try:
                    if ingest_content(db.session, object_type=object_type, raw_data=raw):
                        query_stored += 1
                except Exception as e:
                    logger.critical(f"[{source_name}] FATAL: Ingestion failed.")
                    raise PipelineFatalError(f"Database error: {str(e)}") from e
            
            total_stored += query_stored
            if query_stored > 0:
                print(f"    -> Stored {query_stored} new {object_type}s")

        except (PipelineFatalError, PipelineQuotaExceededError):
            raise
        except Exception:
            logger.exception(f"[{source_name}] Failed query: {q_text}")

    return total_stored
