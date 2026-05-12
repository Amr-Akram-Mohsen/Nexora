import logging
import random
import time
from datetime import datetime
from typing import Callable, List, Dict, Optional
from flask import current_app
from .ingestion.ports import DiscoveryPort, FetcherPort, EnrichmentPort, QuotaPort, CooldownPort, ClassificationPort
from .ingestion import ingest_content
from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError
from app.shared.utils.logging import log_fetch_query_error

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
            logger.info(
                "[FETCH][%s] skip  reason=no_queries_discovered  source_filter=%s"
                "  hint=check_CATEGORY_SOURCE_OVERRIDES_and_DEFAULT_SOURCE_ALIGNMENT",
                self.source_name, source_filter,
            )
            return 0

        def get_fresh_tasks(tasks):
            cooldown_hrs = fetch_params.get("cooldown_hours", 6)
            fresh = []
            for sec, cat, q_obj in tasks:
                q_text = q_obj.get("query", "")
                cache_key = f"{source_filter}:{cat}:{q_text}"
                if self.cooldown_service.should_refetch(sec, cache_key, hours=cooldown_hrs):
                    fresh.append((sec, cat, q_obj))
            return fresh

        # ── Taxonomy-group batching & Cooldown filtering ──────────────────────
        group: str = ""
        batch_state = None
        cooldown_hrs = fetch_params.get("cooldown_hours", 6)

        try:
            from app.shared.utils.batch_state import BatchState
            batch_state = BatchState(source_filter)
        except Exception as exc:
            logger.warning("[FETCH][%s] batch state unavailable — running ungrouped  err=%s", self.source_name, exc)

        if batch_state:
            # We try to find a group that has fresh tasks. 
            # We check up to len(_TAXONOMY_GROUPS) to avoid infinite loops if everything is on cooldown.
            groups_checked = 0
            while groups_checked < len(_TAXONOMY_GROUPS):
                group = batch_state.current_group(_TAXONOMY_GROUPS) or ""
                if not group:
                    break
                
                # Filter tasks for this group
                group_tasks = [
                    (sec, cat, q) for sec, cat, q in flat_tasks
                    if cat.startswith(group) or group in cat
                ]
                
                if not group_tasks:
                    logger.info("[FETCH][%s] group %s has no allowed queries for this source — skipping", self.source_name, group)
                    batch_state.advance(_TAXONOMY_GROUPS)
                    groups_checked += 1
                    continue
                
                fresh_group_tasks = get_fresh_tasks(group_tasks)
                if fresh_group_tasks:
                    flat_tasks = fresh_group_tasks
                    logger.info(
                        "[FETCH][%s] batch group=%s  eligible_queries=%d/%d",
                        self.source_name, group, len(flat_tasks), len(group_tasks)
                    )
                    break # Found a productive group
                else:
                    logger.info(
                        "[FETCH][%s] group %s is skipped (all %d queries are on cooldown or inactive)", 
                        self.source_name, group, len(group_tasks)
                    )
                    batch_state.advance(_TAXONOMY_GROUPS)
                    groups_checked += 1
            
            if groups_checked >= len(_TAXONOMY_GROUPS):
                logger.info(
                    "[FETCH][%s] skip  reason=all_groups_cooldown  groups_checked=%d  source_filter=%s",
                    self.source_name, groups_checked, source_filter,
                )
                return 0
        else:
            # Ungrouped fallback
            total_before = len(flat_tasks)
            flat_tasks = get_fresh_tasks(flat_tasks)
            if not flat_tasks:
                logger.info(
                    "[FETCH][%s] skip  reason=all_queries_cooldown  total_queries_blocked=%d  source_filter=%s",
                    self.source_name, total_before, source_filter,
                )
                return 0

        # ── Apply limit cap ──────────────────────────────────────────
        total_eligible = len(flat_tasks)
        if limit and limit < len(flat_tasks):
            random.shuffle(flat_tasks)
            flat_tasks = flat_tasks[:limit]

        total_tasks = len(flat_tasks)

        # ── Run banner (full date+time stamps this run) ──────────────
        logger.info(
            "=== [FETCH][%s]  %s  group=%-12s  tasks=%d/%d  limit=%s ===",
            self.source_name,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            group or "(all)",
            total_tasks, total_eligible,
            limit or "inf",
        )

        # ── Main loop ─────────────────────────────────────────────────
        total_stored = 0
        total_updated = 0
        completed = 0
        t_run = time.monotonic()

        for section, category, q_obj in flat_tasks:
            q_text = q_obj.get("query", "")
            t_q = time.monotonic()

            stored_n = updated_n = fetched_n = 0
            try:
                stored_n, updated_n, fetched_n = self._process_query(
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
                session.rollback()
                logger.info(
                    "  [%d/%d] %-44s fetched=%-3d  stored=%d  updated=%d  (%.1fs) X halted",
                    completed + 1, total_tasks, f'"{q_text[:40]}"',
                    0, 0, 0, time.monotonic() - t_q,
                )
                raise
            except Exception as exc:
                log_fetch_query_error(logger, self.source_name, query=q_text, error=exc, group=group)
                session.rollback()

            completed += 1
            total_stored += stored_n
            total_updated += updated_n
            logger.info(
                "  [%d/%d] %-44s fetched=%-3d  stored=%d  updated=%d  (%.1fs)",
                completed, total_tasks, f'"{q_text[:40]}"',
                fetched_n, stored_n, updated_n, time.monotonic() - t_q,
            )

        # ── Advance cursor + run footer ───────────────────────────────
        next_group = ""
        if batch_state is not None and completed > 0:
            try:
                batch_state.advance(_TAXONOMY_GROUPS)
                next_group = _TAXONOMY_GROUPS[batch_state.cursor]
            except Exception as exc:
                logger.warning("[FETCH][%s] could not advance batch cursor  err=%s", self.source_name, exc)

        logger.info(
            "=== [FETCH][%s] DONE   stored=%-3d  updated=%-3d  elapsed=%.1fs  -> next=%s ===",
            self.source_name, total_stored, total_updated,
            time.monotonic() - t_run,
            next_group or group or "(all)",
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
    ) -> tuple:
        """
        Run one query through the full pipeline: cooldown → fetch → classify → enrich → ingest.
        Returns (stored, updated, fetched) counts.
        Raises on fatal/quota errors so the caller can halt the run.
        """
        q_text = q_obj.get("query", "")
        cache_key = f"{source_filter}:{category}:{q_text}"

        # 1. Cooldown check
        cooldown_hrs = fetch_params.get("cooldown_hours", 6)
        if not self.cooldown_service.should_refetch(section, cache_key, hours=cooldown_hrs):
            return 0, 0, 0

        # 2. Quota check
        if not self.quota_service.can_call():
            logger.warning("[FETCH][%s] quota exhausted — halting run", self.source_name)
            raise PipelineQuotaExceededError(f"{self.source_name} quota exhausted")

        # 3. Fetch
        sanitized_params = {k: v for k, v in fetch_params.items() if k != "cooldown_hours"}
        
        # Load conditional fetch metadata
        meta = self.cooldown_service.get_fetch_metadata(section, cache_key)
        if meta:
            sanitized_params.update({
                "etag": meta.get("etag"),
                "modified": meta.get("last_modified")
            })

        try:
            response = fetcher(q_obj, **sanitized_params)
            self.quota_service.record_call()

            # Handle both list and dict response types
            if isinstance(response, dict):
                raw_items = response.get("items", [])
                new_etag = response.get("etag")
                new_modified = response.get("modified")
            else:
                raw_items = response
                new_etag = None
                new_modified = None

            self.cooldown_service.mark_fetched(
                section, cache_key,
                category=category,
                source=source_filter,
                normalized_query=q_text,
                etag=new_etag,
                last_modified=new_modified,
                had_results=bool(raw_items),   # ← do NOT count empty responses as successes
            )
        except Exception as e:
            self.cooldown_service.mark_failed(section, cache_key, error=e, source=source_filter)
            from app.integrations.exceptions import PipelineFatalError, PipelineQuotaExceededError
            if isinstance(e, (PipelineFatalError, PipelineQuotaExceededError)):
                raise
            log_fetch_query_error(logger, source_filter, query=q_text, error=e)
            return 0, 0, 0

        # 4. Process each raw item
        query_stored = 0
        query_updated = 0

        for raw in raw_items:
            item_title = _safe_title(raw)
            logger.debug("[FETCH][%s] processing  title=\"%s\"", self.source_name, item_title)

            if hasattr(raw, "model_dump"):
                raw = raw.model_dump()
            elif hasattr(raw, "dict"):
                raw = raw.dict()

            classified = self.classification_service(raw, section, category, q_obj)
            enriched = self.enrichment_service(classified, section, category, q_obj)

            if hasattr(enriched, "model_dump"):
                enriched_dict = enriched.model_dump()
            elif hasattr(enriched, "dict"):
                enriched_dict = enriched.dict()
            else:
                enriched_dict = enriched

            missing = [k for k in ("url", "title") if not enriched_dict.get(k)]
            if missing:
                logger.warning(
                    "[FETCH][%s] missing fields=%s  title=\"%s\"",
                    self.source_name, missing, item_title,
                )

            try:
                if object_type == "article":
                    if not enriched_dict.get("is_content_scraped") or not enriched_dict.get("image_url"):
                        enriched_dict["status"] = "pending"
                        enriched_dict["is_published"] = False
                    else:
                        enriched_dict["status"] = "complete"
                        enriched_dict["is_published"] = True
                else:
                    has_visual = bool(enriched_dict.get("thumbnail_url") or enriched_dict.get("image_url"))
                    enriched_dict["is_published"] = has_visual

                result = ingest_content(session, object_type=object_type, raw_data=enriched_dict)
                if result:
                    content_obj, is_new = result
                    if is_new:
                        query_stored += 1
                        logger.info(
                            "[INGEST][%s] +stored  \"%.55s\"  published=%s",
                            self.source_name, item_title,
                            enriched_dict.get("is_published", False),
                        )
                    else:
                        query_updated += 1
                else:
                    logger.debug(
                        "[INGEST][%s] skip  reason=duplicate_or_invalid  title=\"%s\"",
                        self.source_name, item_title,
                    )
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

        return query_stored, query_updated, len(raw_items)


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
