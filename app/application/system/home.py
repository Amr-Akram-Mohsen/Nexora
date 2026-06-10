"""
Homepage data orchestration.

Assembles all data needed by index.html from domain services.

Section keys returned by ``get_home_page_data()``:

  Content sections
  ────────────────
  hero_sliders          — Trends section content (for the hero slider)
  latest_reviews        — Most recent reviews
  tech_news             — Most recent news content
  tutorials             — Tutorial content
  popular_this_week     — Trending content across all sections (7-day window)
  recommended_videos    — Trending video content specifically
  recommended_articles  — Trending article content specifically
  editors_picks         — Content with the highest editorial score

  Item sections
  ─────────────
  top_deals             — Items with a discounted variant price
  recently_added        — Newest items
  featured_products     — Items ranked by recent views + clicks

  Taxonomy sections
  ─────────────────
  trending_brands       — Brands ranked by content view-count (7-day window)
"""
from app.application.content.query_service import get_contents_render_cached
from app.application.recommendation.query_service import (
    get_trending_contents_cached_v2,
    get_editors_picks_cached,
    get_trending_items_cached,
    get_trending_brands_cached,
)
from app.domains.item.service import get_filtered_items_for_home
from app.infrastructure import cache


@cache.cached(timeout=300, key_prefix="home_page_data")
def get_home_page_data():
    """
    Orchestrates data for the home page.

    All heavy lifting is delegated to domain services and application-layer
    cached wrappers. This function only assembles the final dict.
    """
    # ── Existing content sections ─────────────────────────────────────────
    hero_contents  = get_contents_render_cached(filter_values=("trends",),    rows_count=5)
    latest_reviews = get_contents_render_cached(filter_values=("reviews",),   rows_count=24)
    tech_news      = get_contents_render_cached(filter_values=("news",),      rows_count=24)
    tutorials      = get_contents_render_cached(filter_values=("tutorials",), rows_count=24)

    # ── New: discovery sections ───────────────────────────────────────────
    # Trending across all sections (last 7 days)
    popular_this_week    = get_trending_contents_cached_v2(limit=8, days=7)

    # Type-specific trending feeds
    recommended_videos   = get_trending_contents_cached_v2(limit=8, days=14, object_type="video")
    recommended_articles = get_trending_contents_cached_v2(limit=8, days=14, object_type="article")

    # Editorial picks (high Content.score)
    editors_picks        = get_editors_picks_cached(limit=6)

    # ── Existing item sections ────────────────────────────────────────────
    top_deals      = get_filtered_items_for_home(filter_type="deals",  limit=10)
    recently_added = get_filtered_items_for_home(filter_type="recent", limit=10)

    # ── New: item discovery sections ──────────────────────────────────────
    featured_products    = get_trending_items_cached(limit=8, days=7)

    # ── New: brand discovery section ──────────────────────────────────────
    trending_brands      = get_trending_brands_cached(limit=6, days=7)

    return {
        # ── Hero ───────────────────────────────────────────────────────────
        "hero_sliders": hero_contents,

        # ── Content ────────────────────────────────────────────────────────
        "latest_reviews": latest_reviews,
        "tech_news": tech_news,
        "tutorials": tutorials,
        "popular_this_week": popular_this_week,
        "recommended_videos": recommended_videos,
        "recommended_articles": recommended_articles,
        "editors_picks": editors_picks,

        # ── Items ──────────────────────────────────────────────────────────
        "top_deals": top_deals,
        "recently_added": recently_added,
        "featured_products": featured_products,

        # ── Brands ─────────────────────────────────────────────────────────
        "trending_brands": trending_brands,
    }
