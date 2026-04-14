# app/scrapers/runner.py
"""
Orchestrates all scraper/discovery jobs.
Balanced discovery across Electronics, Perfumes, and Accessories.
Fails gracefully if API keys are missing.
"""
import logging
from flask import current_app

logger = logging.getLogger(__name__)


def run_article_fetch():
    """Fetch all free sources + YouTube with a diverse set of tech/fragrance/fashion queries."""
    # ── NewsAPI (Requires Key) ───────────────────────────────────
    if current_app.config.get("NEWS_API_KEY"):
        try:
            from .newsapi import fetch_all_sections as fetch_newsapi
            logger.info("[Runner] NewsAPI...")
            fetch_newsapi()
        except Exception:
            logger.exception("[Runner] NewsAPI fetch failed")
    else:
        logger.info("[Runner] Skipping NewsAPI: Key missing")

    # ── GNews (Requires Key) ──────────────────────────────────────
    if current_app.config.get("GNEWS_API_KEY"):
        try:
            from .gnews_fetcher import fetch_all_gnews
            logger.info("[Runner] GNews...")
            fetch_all_gnews()
        except Exception:
            logger.exception("[Runner] GNews fetch failed")
    else:
        logger.info("[Runner] Skipping GNews: Key missing")

    # ── YouTube (Requires Key) ───────────────────────────────────
    if current_app.config.get("YOUTUBE_API_KEY"):
        try:
            from .youtube_fetcher import fetch_youtube_reviews
            logger.info("[Runner] YouTube reviews...")
            fetch_youtube_reviews()
        except Exception:
            logger.exception("[Runner] YouTube fetch failed")
    else:
        logger.info("[Runner] Skipping YouTube: Key missing")

    # ── RSS (Always Runs) ──────────────────────────────────────────
    try:
        from .rss_fetcher import fetch_all_rss
        logger.info("[Runner] RSS feeds...")
        count = fetch_all_rss()
        logger.info("[Runner] RSS done — %d articles stored", count)
    except Exception:
        logger.exception("[Runner] RSS fetch failed")



def run_reddit_fetch():
    """Fetch community posts from diverse subreddits."""
    # ── Reddit (Disabled for now as per user request) ────────────────
    # if current_app.config.get("REDDIT_CLIENT_ID"):
    #     try:
    #         from .reddit_fetcher import fetch_all_reddit
    #         count = fetch_all_reddit()
    #         logger.info("[Runner] Reddit done — %d posts stored", count)
    #     except Exception:
    #         logger.exception("[Runner] Reddit fetch failed")
    # else:
    logger.info("[Runner] Skipping Reddit: Disabled per user request")


def run_price_refresh():
    """Refresh prices for all Amazon store links using PA-API."""
    if not current_app.config.get("AMAZON_SECRET_KEY"):
        logger.info("[Runner] Skipping Price Refresh: Amazon Keys missing")
        return

    try:
        from .amazon_pa import get_product_by_asin
        from app.models import db, ItemStoreLink, Store
        from datetime import datetime

        links = (
            ItemStoreLink.query
            .join(Store)
            .filter(
                Store.affiliate_network == "Amazon Associates",
                ItemStoreLink.is_active == True,
                ItemStoreLink.external_item_id.isnot(None),
            )
            .all()
        )

        updated = 0
        for link in links:
            marketplace = link.store.country.lower()
            data = get_product_by_asin(link.external_item_id, marketplace)
            if not data: continue
            if data.get("price"): link.price = data["price"]
            if data.get("old_price"): link.old_price = data["old_price"]
            if data.get("availability"): link.availability = data["availability"]
            link.last_checked_at = datetime.utcnow()
            updated += 1
        db.session.commit()
        logger.info("[Runner] Price refresh done — %d links updated", updated)
    except Exception:
        logger.exception("[Runner] Price refresh failed")


def run_amazon_discovery():
    """Discover new products from Amazon."""
    # ── Amazon Discovery (Disabled for now as per user request) ──────
    # if not current_app.config.get("AMAZON_SECRET_KEY"):
    #     logger.info("[Runner] Skipping Amazon Discovery: Amazon Keys missing")
    #     return
    #
    # try:
    #     from .amazon_pa import search_products
    #     from .item_storer import store_amazon_item
    #     SEARCHES = [
    #         ("Samsung Galaxy S25", "sa", "electronics"), ("iPhone 16 pro", "sa", "electronics"),
    #         ("Dior Sauvage parfum", "sa", "perfumes"), ("Versace Eros men", "sa", "perfumes"),
    #         ("Seiko watch automatic", "sa", "accessories"), ("Ray Ban sunglasses", "sa", "accessories"),
    #         ("Samsung Galaxy S25", "ae", "electronics"), ("iPhone 16 pro", "ae", "electronics"),
    #     ]
    #     total_stored = 0
    #     for keywords, marketplace, category_slug in SEARCHES:
    #         products = search_products(keywords, marketplace, category_slug, max_results=10)
    #         for raw in products:
    #             item = store_amazon_item(raw)
    #             if item: total_stored += 1
    #     logger.info("[Runner] Discovery done — %d new items stored", total_stored)
    # except Exception:
    #     logger.exception("[Runner] Amazon discovery failed")
    logger.info("[Runner] Skipping Amazon Discovery: Disabled per user request")


def run_noon_discovery():
    """
    Discover new products from Noon via ArabClicks affiliate network.
    Skipped gracefully if ARABCLICKS_PUBLISHER_ID is not configured.
    """
    if not current_app.config.get("ARABCLICKS_PUBLISHER_ID"):
        logger.info("[Runner] Skipping Noon Discovery: ARABCLICKS_PUBLISHER_ID not set")
        return

    try:
        from .noon_arabclicks import discover_noon_products, seed_arabclicks_stores
        from .item_storer import store_amazon_item  # reuse same storage logic

        # Ensure store rows exist in DB
        new_stores = seed_arabclicks_stores()
        if new_stores:
            logger.info("[Runner] Seeded %d new ArabClicks stores", new_stores)

        # Discovery searches — balanced across SA/AE and categories
        NOON_SEARCHES = [
            ("Samsung Galaxy", "noon-sa"),
            ("iPhone 16",      "noon-sa"),
            ("Dior Sauvage",   "noon-sa"),
            ("Nike shoes men", "noon-ae"),
            ("Sony headphones","noon-ae"),
        ]

        total_stored = 0
        for keywords, store_slug in NOON_SEARCHES:
            products = discover_noon_products(keywords, store_slug, max_results=10)
            for raw in products:
                item = store_amazon_item(raw)  # same format, compatible storer
                if item:
                    total_stored += 1

        logger.info("[Runner] Noon Discovery done — %d new items stored", total_stored)
    except Exception:
        logger.exception("[Runner] Noon Discovery failed")


def run_arabclicks_price_refresh():
    """
    Refresh prices for all ArabClicks store links.
    Skipped gracefully if ARABCLICKS_PUBLISHER_ID is not configured.
    """
    if not current_app.config.get("ARABCLICKS_PUBLISHER_ID"):
        logger.info("[Runner] Skipping ArabClicks Price Refresh: Publisher ID not set")
        return

    try:
        from .noon_arabclicks import refresh_noon_prices
        updated = refresh_noon_prices()
        logger.info("[Runner] ArabClicks price refresh done — %d links updated", updated)
    except Exception:
        logger.exception("[Runner] ArabClicks price refresh failed")

