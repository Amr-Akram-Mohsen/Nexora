from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class SourceProfile:
    # Core identity
    content_type: str
    transport: str

    # Execution control
    cooldown_hours: float
    fetch_limit: int

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

    # Allowed taxonomy sections
    allowed_sections: Optional[List[str]] = None



