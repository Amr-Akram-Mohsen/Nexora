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
    "newsapi_ai": SourceProfile(
        content_type="article",
        transport="api",
        cooldown_hours=6,
        max_queries_per_run=20,
        requires_scraping=True,
        freshness_priority="very_high",
        quality_weight=0.90,
        empty_result_penalty=True,
        expected_media=["image"],
        dedupe_strategy=["er_uri", "canonical_url", "normalized_url"],
        allowed_sections=["news", "deals", "trends"],
    ),
    "youtube": SourceProfile(
        content_type="video",
        transport="api",
        cooldown_hours=24,
        max_queries_per_run=50,
        quota_cost=100,
        requires_scraping=False,
        freshness_priority="medium",
        quality_weight=0.90,
        expected_media=["thumbnail"],
        dedupe_strategy=["external_id", "normalized_url"],
        allowed_sections=["reviews", "guides", "deals", "community", "trends"],
    ),
}
