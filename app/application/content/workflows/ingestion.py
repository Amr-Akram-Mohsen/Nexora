import logging
import time
from typing import List, Dict, Optional, Callable
from ..ingestion.services import (
    DiscoveryService,
    EnrichmentService,
    TaxonomyEnrichmentService,
    GenericQuotaService,
    GNewsQuotaService,
    YouTubeQuotaService,
    NewsApiQuotaService,
    CooldownService,
    ClassificationService,
)
from ..ingestion.ports import FetcherPort
from ..ingestion import ingest_content
from app.integrations.content.exceptions import (
    PipelineFatalError,
    PipelineQuotaExceededError,
)
from app.shared.utils.logging import (
    log_fetch_query_error,
    log_fetch_run_start,
    log_fetch_run_done,
    log_item_ingested,
    log_item_skipped,
    log_quota_exhausted,
    log_velocity_cooldown,
)
from app.shared.utils.query_cursor_state import QueryCursorState
from app.shared.constants.source_profiles import SOURCE_PROFILES
from app.shared.constants.query_intelligence import (
    CATEGORY_VELOCITY,
    VELOCITY_COOLDOWN_MULTIPLIER,
)

logger = logging.getLogger(__name__)

# Taxonomy parent-group order used for round-robin rotation.
# Matches the top-level category names in TAXONOMY["categories"].
_TAXONOMY_GROUPS = ["electronics", "perfumes", "accessories"]

QUOTA_SERVICE_MAP = {
    "newsapi": NewsApiQuotaService,
    "newsapi_ai": NewsApiQuotaService,
    "gnews": GNewsQuotaService,
    "youtube": YouTubeQuotaService,
}


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
    ):
        self.source_name = source_name
        self.discovery = None if source_name == "rss" else DiscoveryService()
        self.quota_service = QUOTA_SERVICE_MAP.get(source_name, GenericQuotaService)()
        self.enrichment_service = EnrichmentService()
        self.taxonomy_enrichment_service = TaxonomyEnrichmentService()
        self.cooldown_service = CooldownService()
        self.classification_service = ClassificationService()
        self.profile = SOURCE_PROFILES[source_name]

        logger.info(
            "[FETCH][%s] run started  max_queries_per_run=%s",
            self.source_name,
            self.profile.max_queries_per_run,
        )

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(
        self,
        session,
        object_type: str,
        fetcher: Callable,
        limit: Optional[int] = None,
        **fetch_params,
    ) -> int:
        """
        Execute the ingestion workflow for a single fetch run.

        ``limit`` caps how many queries from the fresh task list actually
        execute this run (burst protection).  When not explicitly provided,
        the profile's ``max_queries_per_run`` is used automatically.

        Returns the number of newly stored content products.
        """
        # Apply burst cap from profile unless an explicit override is provided.
        if limit is None:
            limit = self.profile.max_queries_per_run

        queries_registry = self.discovery.get_queries_by_section(
            source_filter=self.source_name
        )

        # # ── Build flat task list ──────────────────────────────────────
        # flat_tasks = []
        # for section, categories in queries_registry.items():
        #     for category, queries in categories.items():
        #         for q in queries:
        #             flat_tasks.append((section, category, q))

        cursor_state = QueryCursorState(self.source_name)
        flat_tasks = []

        for section, categories in queries_registry.items():
            for category, queries in categories.items():
                last_index = cursor_state.get(section, category)

                start = last_index
                total = len(queries)

                # deterministic slice from last position
                ordered = queries[start:] + queries[:start]

                for i, q in enumerate(ordered):
                    flat_tasks.append(
                        (section, category, q, (start + i) % total, total)
                    )

        if not flat_tasks:
            logger.info(
                "[FETCH][%s] skip  reason=no_queries_discovered  hint=check_CATEGORY_SOURCE_OVERRIDES_and_DEFAULT_SOURCE_ALIGNMENT",
                self.source_name,
            )
            return 0

        def get_fresh_tasks(tasks):
            fresh = []
            for sec, cat, q_obj, idx, total in tasks:
                q_text = q_obj.get("query", "")
                # Extract the leaf category slug from composite "group:leaf" key
                cat_slug = cat.split(":")[-1] if ":" in cat else cat
                velocity = CATEGORY_VELOCITY.get(cat_slug, "medium")
                multiplier = VELOCITY_COOLDOWN_MULTIPLIER.get(velocity, 1.0)
                effective_cooldown = self.profile.cooldown_hours * multiplier
                cache_key = f"{self.source_name}:{cat}:{q_text}"
                if self.cooldown_service.should_refetch(
                    sec, cache_key, hours=effective_cooldown
                ):
                    fresh.append((sec, cat, q_obj, idx, total))
            return fresh

        # ── Taxonomy-group batching & Cooldown filtering ──────────────────────
        group: str = ""
        batch_state = None

        try:
            from app.shared.utils.batch_state import BatchState

            batch_state = BatchState(self.source_name)
        except Exception as exc:
            logger.warning(
                "[FETCH][%s] batch state unavailable — running ungrouped  err=%s",
                self.source_name,
                exc,
            )

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
                    (sec, cat, q, idx, total)
                    for sec, cat, q, idx, total in flat_tasks
                    if cat.startswith(group) or group in cat
                ]

                if not group_tasks:
                    logger.info(
                        "[FETCH][%s] group %s has no allowed queries for this source — skipping",
                        self.source_name,
                        group,
                    )
                    batch_state.advance(_TAXONOMY_GROUPS)
                    groups_checked += 1
                    continue

                fresh_group_tasks = get_fresh_tasks(group_tasks)
                if fresh_group_tasks:
                    flat_tasks = fresh_group_tasks
                    logger.info(
                        "[FETCH][%s] batch group=%s  eligible_queries=%d/%d",
                        self.source_name,
                        group,
                        len(flat_tasks),
                        len(group_tasks),
                    )
                    break  # Found a productive group
                else:
                    logger.info(
                        "[FETCH][%s] group %s is skipped (all %d queries are on cooldown or inactive)",
                        self.source_name,
                        group,
                        len(group_tasks),
                    )
                    batch_state.advance(_TAXONOMY_GROUPS)
                    groups_checked += 1

            if groups_checked >= len(_TAXONOMY_GROUPS):
                logger.info(
                    "[FETCH][%s] skip  reason=all_groups_cooldown  groups_checked=%d",
                    self.source_name,
                    groups_checked,
                )
                return 0
        else:
            # Ungrouped fallback
            total_before = len(flat_tasks)
            flat_tasks = get_fresh_tasks(flat_tasks)

            if not flat_tasks:
                logger.info(
                    "[FETCH][%s] skip  reason=all_queries_cooldown  total_queries_blocked=%d",
                    self.source_name,
                    total_before,
                )
                return 0

        # ── Apply burst-protection cap ────────────────────────────────
        # We apply Dynamic Category Quotas with Weighted Round-Robin
        # This prevents high-velocity categories from starving low-velocity ones
        # while still honoring their priority (high gets more slots per pass).
        total_eligible = len(flat_tasks)
        if limit and limit < len(flat_tasks):
            cat_queues = {}
            for task in flat_tasks:
                sec_cat = (task[0], task[1])
                cat_queues.setdefault(sec_cat, []).append(task)
            
            cat_list = list(cat_queues.keys())
            cat_weights = {}
            for sec_cat in cat_list:
                cat_slug = sec_cat[1].split(":")[-1] if ":" in sec_cat[1] else sec_cat[1]
                velocity = CATEGORY_VELOCITY.get(cat_slug, "medium")
                # Weight mapping: high=3, medium=2, low=1
                cat_weights[sec_cat] = 3 if velocity == "high" else 2 if velocity == "medium" else 1

            # Rotate starting category to prevent the first taxonomy products from dominating
            try:
                from app.shared.utils.rotation_state import RotationState
                rotator = RotationState("category_batch")
                rot_key = f"{self.source_name}_{group or 'all'}"
                start_idx = rotator.state.get(rot_key, 0)
                if start_idx >= len(cat_list):
                    start_idx = 0
                
                cat_list = cat_list[start_idx:] + cat_list[:start_idx]
                rotator.state[rot_key] = (start_idx + 1) % max(1, len(cat_list))
                rotator._save()
            except Exception as exc:
                logger.warning("[FETCH][%s] Could not rotate categories: %s", self.source_name, exc)

            selected = []
            while len(selected) < limit and cat_queues:
                for sec_cat in list(cat_list):
                    if len(selected) >= limit:
                        break
                    if sec_cat not in cat_queues:
                        continue
                    
                    weight = cat_weights[sec_cat]
                    queue = cat_queues[sec_cat]
                    
                    popped = 0
                    while popped < weight and queue and len(selected) < limit:
                        selected.append(queue.pop(0))
                        popped += 1
                        
                    if not queue:
                        del cat_queues[sec_cat]
                        cat_list.remove(sec_cat)
                        
            flat_tasks = selected

        total_tasks = len(flat_tasks)

        # ── Run banner ────────────────────────────────────────────────
        log_fetch_run_start(
            logger,
            self.source_name,
            group=group or "(all)",
            tasks=total_tasks,
            eligible=total_eligible,
            limit=limit or "inf",
        )
        # ── Main loop ─────────────────────────────────────────────────
        total_stored = 0
        total_updated = 0
        completed = 0
        t_run = time.monotonic()

        for section, category, q_obj, idx, total in flat_tasks:
            q_text = q_obj.get("query", "")
            t_q = time.monotonic()

            stored_n = updated_n = fetched_n = 0
            try:
                stored_n, updated_n, fetched_n = self._process_query(
                    session=session,
                    object_type=object_type,
                    fetcher=fetcher,
                    section=section,
                    category=category,
                    q_obj=q_obj,
                    fetch_params=fetch_params,
                )

                # FIX: advance to next query (not just record current index)
                cursor_state.update(section, category, idx, total)
            except (PipelineFatalError, PipelineQuotaExceededError):
                session.rollback()
                logger.warning(
                    "[FETCH][%s] query_halted [%d/%d] %s  (%.1fs)",
                    self.source_name,
                    completed + 1,
                    total_tasks,
                    f'"{q_text[:60]}"',
                    time.monotonic() - t_q,
                )
                raise
            except Exception as exc:
                log_fetch_query_error(
                    logger, self.source_name, query=q_text, error=exc, group=group
                )
                session.rollback()

            completed += 1
            total_stored += stored_n
            total_updated += updated_n
            logger.info(
                "[FETCH][%s] query_done [%d/%d] %s  fetched=%d  stored=%d  updated=%d  (%.1fs)",
                self.source_name,
                completed,
                total_tasks,
                f'"{q_text}"',
                fetched_n,
                stored_n,
                updated_n,
                time.monotonic() - t_q,
            )

        # ── Advance cursor + run footer ───────────────────────────────
        next_group = ""
        if batch_state is not None and completed > 0:
            try:
                batch_state.advance(_TAXONOMY_GROUPS)
                next_group = _TAXONOMY_GROUPS[batch_state.cursor]
            except Exception as exc:
                logger.warning(
                    "[FETCH][%s] could not advance batch cursor  err=%s",
                    self.source_name,
                    exc,
                )

        cursor_state.commit()
        log_fetch_run_done(
            logger,
            self.source_name,
            stored=total_stored,
            updated=total_updated,
            elapsed=time.monotonic() - t_run,
            next_group=next_group or group or "(all)",
        )

        if total_stored > 0:
            try:
                from app.infrastructure.cache.content import invalidate_content_after_write

                invalidate_content_after_write()
                logger.info(
                    "[FETCH][%s] Invalidated cached content listings and filter options due to new content ingestion.",
                    self.source_name,
                )
            except Exception as exc:
                logger.warning(
                    "[FETCH][%s] Cache invalidation failed: %s",
                    self.source_name,
                    exc,
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
        # source_filter: str,
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
        cat_slug = category.split(":")[-1] if ":" in category else category
        velocity = CATEGORY_VELOCITY.get(cat_slug, "medium")
        multiplier = VELOCITY_COOLDOWN_MULTIPLIER.get(velocity, 1.0)
        effective_cooldown = self.profile.cooldown_hours * multiplier
        cache_key = f"{self.source_name}:{category}:{q_text}"

        if effective_cooldown != self.profile.cooldown_hours:
            log_velocity_cooldown(
                logger,
                self.source_name,
                category=cat_slug,
                velocity=velocity,
                base_hours=self.profile.cooldown_hours,
                effective_hours=effective_cooldown,
            )

        # 1. Cooldown check (velocity-scaled)
        if not self.cooldown_service.should_refetch(
            section, cache_key, hours=effective_cooldown
        ):
            return 0, 0, 0

        # 2. Quota check
        if not self.quota_service.can_call():
            log_quota_exhausted(logger, self.source_name)
            raise PipelineQuotaExceededError(f"{self.source_name} quota exhausted")

        # 3. Fetch
        sanitized_params = {
            k: v for k, v in fetch_params.items() if k != "cooldown_hours"
        }

        # Load conditional fetch metadata
        meta = self.cooldown_service.get_fetch_metadata(section, cache_key)
        if meta:
            sanitized_params.update(
                {"etag": meta.get("etag"), "modified": meta.get("last_modified")}
            )

        try:
            response = fetcher(q_obj, **sanitized_params)
            self.quota_service.record_call()

            # Handle both list and dict response types
            if isinstance(response, dict):
                raw_items = response.get("products", [])
                new_etag = response.get("etag")
                new_modified = response.get("modified")
            else:
                raw_items = response
                new_etag = None
                new_modified = None

            self.cooldown_service.mark_fetched(
                section,
                cache_key,
                category=category,
                source=self.source_name,
                normalized_query=q_text,
                etag=new_etag,
                last_modified=new_modified,
                had_results=bool(
                    raw_items
                ),  # ← do NOT count empty responses as successes
            )
        except Exception as e:
            self.cooldown_service.mark_failed(
                section, cache_key, error=e, source=self.source_name
            )
            if isinstance(e, (PipelineFatalError, PipelineQuotaExceededError)):
                raise
            log_fetch_query_error(logger, self.source_name, query=q_text, error=e)
            return 0, 0, 0

        # 4. Process each raw product
        query_stored = 0
        query_updated = 0

        for raw in raw_items:
            item_title = _safe_title(raw)

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

            # ── Taxonomy Enrichment (post-normalization, pre-persistence) ──
            # Refines category, topics, brands, and facets using content
            # signals.  Runs after normalization so it can see the final
            # content text; runs before persistence so DB records are correct.
            # Failures are caught internally and fall back silently.
            enriched_dict = self.taxonomy_enrichment_service(enriched_dict)

            enriched_dict["ingestion_origin"] = self.source_name

            missing = [k for k in ("url", "title") if not enriched_dict.get(k)]
            if missing:
                log_item_skipped(
                    logger,
                    self.source_name,
                    item_title,
                    reason="missing_required_fields",
                    missing=missing,
                )

            try:
                if object_type == "article":
                    # Phase 1: All articles start as discovered and wait for Diffbot enrichment
                    enriched_dict["status"] = "discovered"
                    enriched_dict["is_published"] = False
                else:
                    has_visual = bool(
                        enriched_dict.get("thumbnail_url")
                        or enriched_dict.get("image_url")
                    )
                    enriched_dict["is_published"] = has_visual

                result = ingest_content(
                    session, object_type=object_type, raw_data=enriched_dict
                )
                if result:
                    content_obj, status = result
                    if status == "created":
                        query_stored += 1
                        log_item_ingested(
                            logger,
                            self.source_name,
                            content_id=content_obj.id,
                            object_id=content_obj.object_id,
                            status="stored",
                            published=content_obj.is_published if hasattr(content_obj, "is_published") else enriched_dict.get("is_published"),
                        )
                    elif status == "skipped":
                        log_item_skipped(
                            logger,
                            self.source_name,
                            item_title,
                            reason="duplicate_no_changes",
                        )
                    else:
                        query_updated += 1
                        log_item_ingested(
                            logger, self.source_name, content_id=content_obj.id, object_id=content_obj.object_id, status="updated", updated_relationships=status
                        )
                else:
                    log_item_skipped(
                        logger, self.source_name, item_title, reason="ingestion_refused"
                    )
            except Exception as exc:
                import sqlalchemy.exc

                if isinstance(
                    exc,
                    (sqlalchemy.exc.OperationalError, sqlalchemy.exc.InterfaceError),
                ):
                    logger.critical("[FETCH][%s] DB error: %s", self.source_name, exc)
                    raise PipelineFatalError(f"Database error: {exc}") from exc
                log_item_skipped(
                    logger,
                    self.source_name,
                    item_title,
                    reason="ingestion_failed",
                    error=str(exc),
                )

        if query_stored > 0:
            session.commit()

        return query_stored, query_updated, len(raw_items)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_title(raw) -> str:
    """Extract a short display title from a raw product (DTO or dict)."""
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
    api_fetcher: Callable,
    manual_queries: Optional[List[Dict]] = None,
    **extra_params,
) -> int:
    """
    Helper to run an orchestrated ingestion run using injected dependencies.

    Signature is fully backward-compatible with all existing call-sites.
    """
    workflow = IngestionWorkflow(
        source_name=source_name,
    )

    if manual_queries:

        class ManualDiscovery:
            def get_queries_by_section(self, source_filter):  # noqa: N802
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
        fetcher=api_fetcher,
        **extra_params,
    )
