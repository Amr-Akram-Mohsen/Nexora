from .source_profile_model import SourceProfile

# ============================================================
# SOURCE PROFILES
# ============================================================
#
# cooldown_hours
#   How long before the SAME query is allowed to re-fire.
#   Velocity scaling (VELOCITY_COOLDOWN_MULTIPLIER) adjusts this
#   per category:
#     high  → 0.25× (smartphones: 12h → 3h effective)
#     medium → 0.5×  (earbuds:     12h → 6h effective)
#     low   → 2.0×  (niche perfumes: 12h → 24h effective)
#
# max_queries_per_run
#   Hard cap on how many queries actually fire in one execution.
#   This is the BURST protection — prevents a cold-start or cache
#   reset from consuming the entire daily quota at once.
#   Cooldowns handle temporal spreading; this handles the per-run
#   ceiling.
#
#   Sizing:  daily_quota / expected_runs_per_day, with a margin.
#   Example: YouTube = 100 searches/day, run every 3h (8×/day)
#            → safe cap = 100 / 8 = 12.5 → use 10 (with margin)
#
# allowed_sections
#   Secondary discovery gate — only enforced when no explicit
#   CATEGORY_SOURCE_OVERRIDES entry exists for that category+section.
#   Explicit overrides always take precedence.
#
# ============================================================

SOURCE_PROFILES: dict[str, SourceProfile] = {
    "rss": SourceProfile(
        content_type="article",
        transport="feed",
        # RSS uses etag/last-modified — zero cooldown is correct since the
        # protocol itself handles freshness (304 Not Modified).
        cooldown_hours=0,
        # RSS has only a handful of feeds; run them all every cycle.
        max_queries_per_run=25,
        requires_scraping=True,
        supports_etag=True,
        supports_last_modified=True,
        freshness_priority="high",
        quality_weight=0.85,
        empty_result_penalty=False,
        expected_media=["image"],
        dedupe_strategy=["canonical_url", "normalized_url", "title_similarity"],
        allowed_sections=["news", "reviews", "tutorials", "trends"],
    ),
    "newsapi": SourceProfile(
        content_type="article",
        transport="api",
        # 12h base cooldown.
        # Velocity scaling: smartphones → 3h, niche perfumes → 24h.
        cooldown_hours=12,
        # Daily quota: 100 requests.
        # Assuming ~6 meaningful runs/day (after cooldowns thin the pool):
        #   100 / 6 = ~16 → use 15 (conservative margin).
        max_queries_per_run=15,
        requires_scraping=True,
        freshness_priority="very_high",
        quality_weight=0.75,
        empty_result_penalty=True,
        expected_media=["image"],
        dedupe_strategy=["canonical_url", "normalized_url", "title_similarity"],
        allowed_sections=["news", "trends"],
    ),
    "gnews": SourceProfile(
        content_type="article",
        transport="api",
        # 16h base — GNews has a stricter daily quota than NewsAPI.
        # Velocity: smartphones → 4h, niche perfumes → 32h.
        cooldown_hours=16,
        # Daily quota: 100 requests.
        # Pool is smaller (~134 total queries); runs are fewer.
        # 100 / 6 = ~16 → use 12 (extra margin for GNews being quota-sensitive).
        max_queries_per_run=10,
        requires_scraping=True,
        freshness_priority="high",
        quality_weight=0.70,
        empty_result_penalty=True,
        expected_media=["image"],
        dedupe_strategy=["canonical_url", "normalized_url", "title_similarity"],
        allowed_sections=["news", "trends"],
    ),
    "youtube": SourceProfile(
        content_type="video",
        transport="api",
        # 24h base cooldown.
        # Velocity: smartphones → 6h, niche perfumes → 48h (effectively weekly).
        cooldown_hours=24,
        # Daily quota: 10,000 units → 100 searches (each costs 100 units).
        # Query pool: ~1,046 total. Running every 3h = 8 runs/day.
        # Budget per run: 100 / 8 = 12.5 → use 10 (strict — YouTube quota is
        # the most expensive resource in the pipeline).
        # 10 runs × 10 searches × 10 items/search = 1,000 videos/day maximum.
        max_queries_per_run=10,
        quota_cost=100,
        requires_scraping=False,
        freshness_priority="medium",
        quality_weight=0.90,
        expected_media=["thumbnail"],
        dedupe_strategy=["external_id", "normalized_url"],
        allowed_sections=["reviews", "tutorials", "trends", "community"],
    ),
    "reddit": SourceProfile(
        content_type="post",
        transport="api",
        # 8h base cooldown.
        # Velocity: smartphones → 2h, niche perfumes → 16h.
        cooldown_hours=8,
        # Reddit quota: effectively unlimited (OAuth 60 req/min).
        # Cap is for DB write throughput, not API limits.
        max_queries_per_run=25,
        quota_cost=1,
        requires_scraping=False,
        freshness_priority="high",
        quality_weight=0.65,
        expected_media=["thumbnail", "image"],
        dedupe_strategy=["external_id", "normalized_url"],
        allowed_sections=["community", "trends", "reviews"],
    ),
}
