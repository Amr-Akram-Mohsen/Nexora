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

  Product sections
  ─────────────
  top_deals             — Items with a discounted variant price
  recently_added        — Newest products
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
from app.domains.product.service import get_filtered_items_for_home
from app.infrastructure import cache


@cache.cached(timeout=300, key_prefix="home_page_data")
def get_home_page_data():
    """
    Orchestrates data for the home page.

    All heavy lifting is delegated to domain services and application-layer
    cached wrappers. This function assembles the final dict using a 
    cascading deduplication strategy to prevent products from appearing in 
    multiple sections simultaneously.
    """
    seen_content_ids = set()
    seen_product_ids = set()

    def filter_and_track(items_list, seen_set, limit):
        if not items_list:
            return []
        result = []
        for product in items_list:
            product_id = product.get("id")
            if product_id and product_id not in seen_set:
                result.append(product)
                seen_set.add(product_id)
            if len(result) >= limit:
                break
        return result

    # ── Priority 1: High-Intent & Curated ─────────────────────────────────
    editors_picks = filter_and_track(get_editors_picks_cached(limit=12), seen_content_ids, limit=6)
    hero_contents = filter_and_track(get_contents_render_cached(filter_values=("trends",), rows_count=10), seen_content_ids, limit=5)

    # ── Priority 2: High-Value Contextual (Deals) ─────────────────────────
    top_deals = filter_and_track(get_filtered_items_for_home(filter_type="deals", limit=20), seen_product_ids, limit=10)

    # ── Priority 3: Trending & Algorithmic ────────────────────────────────
    popular_this_week = filter_and_track(get_trending_contents_cached_v2(limit=24, days=7), seen_content_ids, limit=8)
    featured_products = filter_and_track(get_trending_items_cached(limit=24, days=7), seen_product_ids, limit=8)

    recommended_videos = filter_and_track(get_trending_contents_cached_v2(limit=24, days=14, object_type="video"), seen_content_ids, limit=8)
    recommended_articles = filter_and_track(get_trending_contents_cached_v2(limit=24, days=14, object_type="article"), seen_content_ids, limit=8)

    # Trending brands is taxonomy, no exclusion needed
    trending_brands = get_trending_brands_cached(limit=6, days=7)

    # ── Priority 4: Chronological & Fillers ───────────────────────────────
    latest_reviews = filter_and_track(get_contents_render_cached(filter_values=("reviews",), rows_count=36), seen_content_ids, limit=24)
    tech_news = filter_and_track(get_contents_render_cached(filter_values=("news",), rows_count=36), seen_content_ids, limit=24)
    tutorials = filter_and_track(get_contents_render_cached(filter_values=("tutorials",), rows_count=36), seen_content_ids, limit=24)
    recently_added = filter_and_track(get_filtered_items_for_home(filter_type="recent", limit=30), seen_product_ids, limit=10)

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
