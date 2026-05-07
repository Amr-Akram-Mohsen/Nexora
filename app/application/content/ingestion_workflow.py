import logging
import random
from typing import Callable, List, Dict, Optional
from flask import current_app
from .ingestion.ports import DiscoveryPort, FetcherPort, EnrichmentPort, QuotaPort, CooldownPort, ClassificationPort
from .ingestion import ingest_content
from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError
from app.shared.utils.logging import (
    log_fetch_query_start,
    log_fetch_progress,
    log_fetch_query_error,
)

logger = logging.getLogger(__name__)

# Taxonomy parent-group order used for round-robin rotation.
# Matches the top-level category names in TAXONOMY["categories"].
_TAXONOMY_GROUPS = ["electronics", "perfumes", "accessories"]


class IngestionWorkflow:
    """
    Centralized workflow for content ingestion.

    Enhancements over the original:
    * Taxonomy-group-aware batching — on each run only queries belonging to
      the *current* parent group (electronics / perfumes / accessories) are
      considered, and a BatchState cursor rotates the active group so
      coverage spreads across executions.
    * Progressive logging — a [FETCH] progress line is emitted after every
      query, so operators can monitor execution in real time.
    * Per-query isolation — if one query's fetcher or enrichment raises an
      unexpected exception it is logged and skipped; the loop continues.
    """

    def __init__(
        self,
        source_name: str,
        discovery: DiscoveryPort,
        quota_service: QuotaPort,
        enrichment_service: EnrichmentPort,
        cooldown_service: CooldownPort,
        classification_service: ClassificationPort,
    ):
        self.source_name = source_name
        self.discovery = discovery
        self.quota_service = quota_service
        self.enrichment_service = enrichment_service
        self.cooldown_service = cooldown_service
        self.classification_service = classification_service

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(
        self,
        session,
        object_type: str,
        source_filter: str,
        fetcher: FetcherPort,
        limit: Optional[int] = None,
        **fetch_params,
    ) -> int:
        """
        Execute the ingestion workflow for a single fetch run.

        Returns the number of newly stored content items.
        """
        queries_registry = self.discovery.get_queries_by_section(source_filter=source_filter)

        # ── Build flat task list ──────────────────────────────────────
        flat_tasks = []
        for section, categories in queries_registry.items():
            for category, queries in categories.items():
                for q in queries:
                    flat_tasks.append((section, category, q))

        if not flat_tasks:
            logger.info("[FETCH][%s] no queries found  source_filter=%s", self.source_name, source_filter)
            return 0

        # ── Taxonomy-group batching ───────────────────────────────────
        #
        # Filter the flat task list to only queries whose *category* slug
        # starts with the active parent group name.  This narrows a run of
        # ~100 queries down to ~20-30 before the hard `limit` cap is applied.
        # The cursor is advanced at the end of every successful run so the
        # next call processes the following group.
        #
        # If the source already delivers a very narrow query set (e.g. RSS
        # with manual_queries), group filtering is skipped transparently.

        group: str = ""
        batch_state = None

        try:
            from app.shared.utils.batch_state import BatchState
            batch_state = BatchState(source_filter)
            group = batch_state.current_group(_TAXONOMY_GROUPS) or ""
        except Exception as exc:
            logger.warning("[FETCH][%s] batch state unavailable — running ungrouped  err=%s", self.source_name, exc)

        if group:
            group_tasks = [
                (sec, cat, q) for sec, cat, q in flat_tasks
                if cat.startswith(group) or group in cat
            ]
            # Fall back to full list if the group produced nothing
            # (e.g. "perfumes" has very few sections that match some sources).
            if group_tasks:
                flat_tasks = group_tasks
                logger.info(
                    "[FETCH][%s] batch group=%s  group_queries=%d  total_available=%d",
                    self.source_name, group, len(flat_tasks),
                    sum(len(qs) for cats in queries_registry.values() for qs in cats.values()),
                )
            else:
                logger.info(
                    "[FETCH][%s] batch group=%s produced 0 queries — using full set",
                    self.source_name, group,
                )
                group = ""  # treat as ungrouped for progress labels

        # ── Apply limit cap ───────────────────────────────────────────
        if limit and limit < len(flat_tasks):
            random.shuffle(flat_tasks)
            flat_tasks = flat_tasks[:limit]

        total_tasks = len(flat_tasks)
        logger.info(
            "[FETCH][%s] run started  tasks=%d  group=%s  limit=%s",
            self.source_name, total_tasks, group or "(all)", limit or "none",
        )

        # ── Main loop ─────────────────────────────────────────────────
        total_stored = 0
        completed = 0

        for section, category, q_obj in flat_tasks:
            q_text = q_obj.get("query", "")
            log_fetch_query_start(logger, self.source_name, query=q_text, group=group)

            try:
                stored_this_query = self._process_query(
                    session=session,
                    object_type=object_type,
                    source_filter=source_filter,
                    fetcher=fetcher,
                    section=section,
                    category=category,
                    q_obj=q_obj,
                    fetch_params=fetch_params,
                )
            except (PipelineFatalError, PipelineQuotaExceededError):
                # Fatal/quota errors bubble up — stop the run immediately.
                session.rollback()
                raise
            except Exception as exc:
                # Unexpected per-query error — log it, skip, keep going.
                log_fetch_query_error(logger, self.source_name, query=q_text, error=exc, group=group)
                session.rollback()
                stored_this_query = 0

            completed += 1
            total_stored += stored_this_query
            log_fetch_progress(
                logger, self.source_name,
                query=q_text,
                completed=completed,
                total=total_tasks,
                stored=stored_this_query,
                group=group,
            )

        # ── Advance batch cursor ──────────────────────────────────────
        if batch_state is not None:
            try:
                batch_state.advance(_TAXONOMY_GROUPS)
            except Exception as exc:
                logger.warning("[FETCH][%s] could not advance batch cursor  err=%s", self.source_name, exc)

        logger.info(
            "[FETCH][%s] run complete  completed=%d/%d  total_stored=%d  group=%s",
            self.source_name, completed, total_tasks, total_stored, group or "(all)",
        )
        return total_stored

    # ------------------------------------------------------------------
    # Per-query processing (isolated so errors don't abort the loop)
    # ------------------------------------------------------------------

    def _process_query(
        self,
        *,
        session,
        object_type: str,
        source_filter: str,
        fetcher: FetcherPort,
        section: str,
        category: str,
        q_obj: dict,
        fetch_params: dict,
    ) -> int:
        """
        Run one query through the full pipeline: cooldown check → fetch →
        classify → enrich → ingest.  Returns the number of new items stored.
        Raises on fatal/quota errors so the caller can decide whether to stop.
        """
        q_text = q_obj.get("query", "")
        cache_key = f"{source_filter}:{category}:{q_text}"

        # 1. Cooldown check
        cooldown_hrs = fetch_params.get("cooldown_hours", 6)
        if not self.cooldown_service.should_refetch(section, cache_key, hours=cooldown_hrs):
            logger.debug("[FETCH][%s] cooldown active  query=\"%s\"", self.source_name, q_text)
            return 0

        # 2. Quota check
        if not self.quota_service.can_call():
            logger.warning("[FETCH][%s] quota exhausted — halting run", self.source_name)
            raise PipelineQuotaExceededError(f"{self.source_name} quota exhausted")

        # 3. Fetch
        sanitized_params = {k: v for k, v in fetch_params.items() if k != "cooldown_hours"}
        raw_items = fetcher(q_obj, **sanitized_params)
        self.quota_service.record_call()
        self.cooldown_service.mark_fetched(
            section, cache_key,
            category=category,
            source=source_filter,
            normalized_query=q_text,
        )

        # 4. Process each raw item
        query_stored = 0
        for raw in raw_items:
            item_title = _safe_title(raw)

            logger.debug("[FETCH][%s] processing  title=\"%s\"", self.source_name, item_title)

            # Normalise DTO → dict for the legacy pipeline
            if hasattr(raw, "model_dump"):
                raw = raw.model_dump()
            elif hasattr(raw, "dict"):
                raw = raw.dict()

            # 4a. Classification
            classified = self.classification_service(raw, section, category, q_obj)

            # 4b. Enrichment
            enriched = self.enrichment_service(classified, section, category, q_obj)

            # Normalise enriched → dict
            if hasattr(enriched, "model_dump"):
                enriched_dict = enriched.model_dump()
            elif hasattr(enriched, "dict"):
                enriched_dict = enriched.dict()
            else:
                enriched_dict = enriched

            # Sanity: warn if critical fields are missing
            missing = [k for k in ("url", "title") if not enriched_dict.get(k)]
            if missing:
                logger.warning(
                    "[FETCH][%s] missing fields=%s  title=\"%s\"",
                    self.source_name, missing, item_title,
                )

            # 4c. Ingest
            try:
                result = ingest_content(session, object_type=object_type, raw_data=enriched_dict)
                if result:
                    content_obj, is_new = result
                    if is_new:
                        query_stored += 1
                        logger.info("[FETCH][%s] stored  title=\"%s\"", self.source_name, item_title)
                    else:
                        logger.debug("[FETCH][%s] updated  title=\"%s\"", self.source_name, item_title)
                else:
                    logger.debug("[FETCH][%s] skipped (dup/invalid)  title=\"%s\"", self.source_name, item_title)
            except Exception as exc:
                import sqlalchemy.exc
                if isinstance(exc, (sqlalchemy.exc.OperationalError, sqlalchemy.exc.InterfaceError)):
                    logger.critical("[FETCH][%s] DB error: %s", self.source_name, exc)
                    raise PipelineFatalError(f"Database error: {exc}") from exc
                logger.error(
                    "[FETCH][%s] item ingestion failed  title=\"%s\"  err=%s",
                    self.source_name, item_title, exc,
                )

        if query_stored > 0:
            session.commit()

        return query_stored


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_title(raw) -> str:
    """Extract a short display title from a raw item (DTO or dict)."""
    title = getattr(raw, "title", None)
    if not title and hasattr(raw, "get"):
        title = raw.get("title", "")
    return str(title)[:60] if title else "untitled"


# ---------------------------------------------------------------------------
# Public factory / convenience function (unchanged signature)
# ---------------------------------------------------------------------------

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
    **extra_params,
) -> int:
    """
    Helper to run an orchestrated ingestion run using injected dependencies.

    Signature is fully backward-compatible with all existing call-sites.
    """
    workflow = IngestionWorkflow(
        source_name=source_name,
        discovery=discovery_service,
        quota_service=quota_service,
        enrichment_service=enrichment_service,
        cooldown_service=cooldown_service,
        classification_service=classification_service,
    )

    if manual_queries:
        class ManualDiscovery:
            def get_queries_by_section(self, source_filter):   # noqa: N802
                registry: dict = {}
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
        **extra_params,
    )
