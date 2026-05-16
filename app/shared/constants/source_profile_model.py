from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class SourceProfile:
    # Core identity
    content_type: str
    transport: str

    # Execution control
    cooldown_hours: float
    # How many queries from the discovery task list are allowed to fire
    # in a single execution run.  Acts as a burst safety cap so a cold
    # start (or cache reset) cannot consume the entire daily API quota in
    # one invocation.  Cooldown hours handle temporal distribution;
    # this handles the per-run ceiling.
    max_queries_per_run: int

    # API cost control
    quota_cost: int = 1

    # Content behavior flags
    requires_scraping: bool = False

    # HTTP optimization
    supports_etag: bool = False
    supports_last_modified: bool = False

    # Ranking / scoring
    freshness_priority: str = "medium"
    quality_weight: float = 0.7
    empty_result_penalty: bool = False

    # Content shaping
    expected_media: Optional[List[str]] = None

    # Deduplication strategy (IMPORTANT for pipeline logic)
    dedupe_strategy: Optional[List[str]] = None

    # Allowed taxonomy sections.
    # Acts as a secondary discovery gate when no CATEGORY_SOURCE_OVERRIDES
    # entry is present for a given category+section pair.  Explicit overrides
    # always take precedence over this hint so curated source/section pairings
    # (e.g. YouTube for perfumes:news) are never silently suppressed.
    allowed_sections: Optional[List[str]] = None


