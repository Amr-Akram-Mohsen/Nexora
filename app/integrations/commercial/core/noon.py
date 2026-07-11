# app/scrapers/noon_arabclicks.py
"""
ArabClicks Affiliate Deep-Link Generator — Phase 4B Stub
==========================================================
ArabClicks (https://www.arabclicks.com) provides an API to convert any
Noon / Namshi / Sivvi product URL into a tracked affiliate deep-link.

HOW IT WORKS:
  1. You register at arabclicks.com and get a Publisher ID.
  2. You call their tracking API with the original store URL.
  3. They return a redirecting affiliate URL that tracks clicks and commissions.

STORES SUPPORTED (via ArabClicks network):
  - Noon SA  (https://www.noon.com/saudi-en/)
  - Noon AE  (https://www.noon.com/uae-en/)
  - Namshi   (https://en-sa.namshi.com/)
  - Mumzworld (https://www.mumzworld.com/en)

TO ACTIVATE:
  1. Sign up at https://www.arabclicks.com
  2. Add your ARABCLICKS_PUBLISHER_ID to your .env file
  3. Uncomment the live code sections marked with # [LIVE]
  4. Call `run_noon_discovery()` from runner.py

CURRENT STATUS: Stub — structure ready, API calls stubbed out.
"""

import logging
from flask import current_app

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported Stores via ArabClicks
# ---------------------------------------------------------------------------
ARABCLICKS_STORES = {
    "noon-sa": {
        "name":     "Noon SA",
        "slug":     "noon-sa",
        "website":  "https://www.noon.com/saudi-en/",
        "country":  "SA",
        "currency": "SAR",
        "logo_url": "https://f.nooncdn.com/s/app/com/noon/images/noon-logo.svg",
        "base_url": "https://www.noon.com/saudi-en/",
    },
    "noon-ae": {
        "name":     "Noon AE",
        "slug":     "noon-ae",
        "website":  "https://www.noon.com/uae-en/",
        "country":  "AE",
        "currency": "AED",
        "logo_url": "https://f.nooncdn.com/s/app/com/noon/images/noon-logo.svg",
        "base_url": "https://www.noon.com/uae-en/",
    },
    "namshi-sa": {
        "name":     "Namshi SA",
        "slug":     "namshi-sa",
        "website":  "https://en-sa.namshi.com/",
        "country":  "SA",
        "currency": "SAR",
        "logo_url": "https://cdn6.namshi.com/images/logos/namshi-logo-ar.svg",
        "base_url": "https://en-sa.namshi.com/",
    },
    "namshi-ae": {
        "name":     "Namshi AE",
        "slug":     "namshi-ae",
        "website":  "https://en.namshi.com/",
        "country":  "AE",
        "currency": "AED",
        "logo_url": "https://cdn6.namshi.com/images/logos/namshi-logo-ar.svg",
        "base_url": "https://en.namshi.com/",
    },
}

# ArabClicks Deep-Link API Endpoint (refer to their official API docs)
ARABCLICKS_API_BASE = "https://api.arabclicks.com/v1"


# ---------------------------------------------------------------------------
# Store Seeding — Call once to ensure Store rows exist in DB
# ---------------------------------------------------------------------------
def seed_arabclicks_stores() -> int:
    """
    Create Store records for all ArabClicks-supported stores if they don't exist.
    Safe to call multiple times (idempotent).
    Returns the number of new stores created.
    """
    from app.core.extensions import db
    from app.domains.product.models import Store

    created = 0
    for store_slug, cfg in ARABCLICKS_STORES.items():
        existing = Store.query.filter_by(slug=store_slug).first()
        if not existing:
            store = Store(
                name=cfg["name"],
                slug=store_slug,
                website=cfg["website"],
                country=cfg["country"],
                currency=cfg["currency"],
                affiliate_network="ArabClicks",
                logo_url=cfg["logo_url"],
                is_active=True,
            )
            db.session.add(store)
            created += 1
            logger.info("[ArabClicks] Created store: %s", cfg["name"])

    if created:
        db.session.commit()

    return created


# ---------------------------------------------------------------------------
# Deep-Link Generation
# ---------------------------------------------------------------------------
def make_affiliate_url(original_url: str, publisher_id: str | None = None) -> str | None:
    """
    Convert a Noon/Namshi product URL into an ArabClicks tracked affiliate URL.

    Args:
        original_url: The raw product URL, e.g. https://www.noon.com/saudi-en/some-product
        publisher_id: Your ArabClicks Publisher ID (falls back to app config)

    Returns:
        Tracked affiliate URL string, or None if unavailable / key missing.

    # [LIVE] Uncomment below once ARABCLICKS_PUBLISHER_ID is set:
    """
    pid = publisher_id or current_app.config.get("ARABCLICKS_PUBLISHER_ID")
    if not pid:
        logger.warning("[ArabClicks] ARABCLICKS_PUBLISHER_ID not set — returning original URL")
        return original_url  # Graceful fallback: return the untracked URL

    # [LIVE] ----------------------------------------------------------------
    # import requests
    # try:
    #     resp = requests.post(
    #         f"{ARABCLICKS_API_BASE}/deeplink",
    #         json={"publisher_id": pid, "url": original_url},
    #         timeout=5,
    #     )
    #     resp.raise_for_status()
    #     data = resp.json()
    #     return data.get("affiliate_url") or original_url
    # except requests.RequestException as e:
    #     logger.error("[ArabClicks] Deep-link API error: %s", e)
    #     return original_url
    # -----------------------------------------------------------------------

    # Stub: return original URL until API is live
    return original_url


# ---------------------------------------------------------------------------
# Product Discovery Stub
# ---------------------------------------------------------------------------
def discover_noon_products(
    keywords: str,
    store_slug: str = "noon-sa",
    max_results: int = 10,
) -> list[dict]:
    """
    Stub for fetching Noon product listings via ArabClicks or Noon's own API.

    In practice you would:
      1. Scrape or call Noon's search results for `keywords`
      2. Convert each product URL to an affiliate link via `make_affiliate_url()`
      3. Return structured product dicts matching the format used by `store_amazon_item()`

    Returns: list of product dicts (empty until implementation is complete)
    """
    publisher_id = current_app.config.get("ARABCLICKS_PUBLISHER_ID")
    if not publisher_id:
        logger.info("[ArabClicks] Skipping Noon discovery: ARABCLICKS_PUBLISHER_ID not set")
        return []

    cfg = ARABCLICKS_STORES.get(store_slug)
    if not cfg:
        logger.warning("[ArabClicks] Unknown store slug: %s", store_slug)
        return []

    logger.info(
        "[ArabClicks] Discovery stub called — keywords=%r store=%s (not yet implemented)",
        keywords, store_slug
    )

    # [LIVE] ----------------------------------------------------------------
    # When you have a way to fetch Noon product search results (scraping or API),
    # iterate over them and build dicts in this shape:
    #
    # return [
    #     {
    #         "asin":          None,         # Noon uses NID, not ASIN
    #         "external_id":   product["id"],
    #         "name":          product["name"],
    #         "brand_name":    product.get("brand"),
    #         "features":      product.get("features", []),
    #         "image_url":     product.get("image_url"),
    #         "price":         product.get("price"),
    #         "old_price":     product.get("was_price"),
    #         "availability":  "In Stock",
    #         "affiliate_url": make_affiliate_url(product["url"]),
    #         "currency":      cfg["currency"],
    #         "country":       cfg["country"],
    #         "marketplace":   store_slug,
    #         "category_slug": "electronics",  # adjust per query
    #     }
    #     for product in raw_results
    # ]
    # -----------------------------------------------------------------------

    return []


# ---------------------------------------------------------------------------
# Price Refresh Stub
# ---------------------------------------------------------------------------
def refresh_noon_prices() -> int:
    """
    Refresh prices for all ArabClicks store links.
    Stub — returns 0 until Noon product API access is available.

    When live: fetch current price by NID (Noon product ID stored in
    ProductStoreLink.external_product_id) and update the record.
    """
    publisher_id = current_app.config.get("ARABCLICKS_PUBLISHER_ID")
    if not publisher_id:
        logger.info("[ArabClicks] Skipping price refresh: ARABCLICKS_PUBLISHER_ID not set")
        return 0

    logger.info("[ArabClicks] Price refresh stub — not yet implemented")
    return 0
