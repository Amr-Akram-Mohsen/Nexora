# app/scrapers/amazon_pa.py
"""
Amazon Product Advertising API (PA-API) 5.0 client.
Used for product discovery and price refreshing.
"""
from paapi5_python_sdk.api.default_api import DefaultApi
from paapi5_python_sdk.models.search_items_request import SearchItemsRequest
from paapi5_python_sdk.models.get_items_request import GetItemsRequest
from paapi5_python_sdk.models.partner_type import PartnerType
from paapi5_python_sdk.models.search_index import SearchIndex
from paapi5_python_sdk.rest import ApiException
from flask import current_app
import logging

logger = logging.getLogger(__name__)

# Marketplace Config: SA (Saudi Arabia) and AE (UAE)
MARKETPLACES = {
    "sa": {
        "host":         "webservices.amazon.sa",
        "region":       "eu-west-1",
        "marketplace":  "www.amazon.sa",
        "currency":     "SAR",
        "country":      "SA",
    },
    "ae": {
        "host":         "webservices.amazon.ae",
        "region":       "eu-west-1",
        "marketplace":  "www.amazon.ae",
        "currency":     "AED",
        "country":      "AE",
    },
}


def _get_api(marketplace: str) -> DefaultApi:
    cfg = MARKETPLACES[marketplace]
    return DefaultApi(
        access_key=current_app.config["AMAZON_ACCESS_KEY"],
        secret_key=current_app.config["AMAZON_SECRET_KEY"],
        host=cfg["host"],
        region=cfg["region"],
    )


def search_products(keywords: str, marketplace: str = "sa", category_query: str = "All", max_results: int = 10) -> list[dict]:
    """Search for products using PA-API. Returns a list of parsed product dicts."""
    cfg = MARKETPLACES.get(marketplace, MARKETPLACES["sa"])
    api = _get_api(marketplace)
    associate_tag = current_app.config.get(f"AMAZON_ASSOCIATE_TAG_{marketplace.upper()}")
    if not associate_tag:
        logger.warning(f"Amazon Associate Tag for {marketplace.upper()} not set")
        return []

    request = SearchItemsRequest(
        partner_tag=associate_tag,
        partner_type=PartnerType.ASSOCIATES,
        keywords=keywords,
        search_index=SearchIndex.ALL,  # Use ALL to cover perfumes and tech
        item_count=max_results,
        resources=[
            "Images.Primary.Large",
            "ItemInfo.Title",
            "ItemInfo.Features",
            "ItemInfo.ByLineInfo",        # brand
            "Offers.Listings.Price",
            "Offers.Listings.SavingBasis",
            "Offers.Listings.Availability.Message",
        ],
    )

    try:
        response = api.search_items(request)
        results = []
        if response.search_result and response.search_result.products:
            for product in response.search_result.products:
                parsed = _parse_item(product, marketplace, cfg, category_query)
                if parsed:
                    results.append(parsed)
        return results
    except ApiException as e:
        logger.error(f"Amazon PA-API Search Error ({marketplace.upper()}): {e}")
        return []


def get_product_by_asin(asin: str, marketplace: str = "sa") -> dict | None:
    """Fetch product details by ASIN (for price refresh)."""
    cfg = MARKETPLACES.get(marketplace, MARKETPLACES["sa"])
    api = _get_api(marketplace)
    associate_tag = current_app.config.get(f"AMAZON_ASSOCIATE_TAG_{marketplace.upper()}")
    if not associate_tag:
        return None

    request = GetItemsRequest(
        partner_tag=associate_tag,
        partner_type=PartnerType.ASSOCIATES,
        product_ids=[asin],
        resources=[
            "Offers.Listings.Price",
            "Offers.Listings.SavingBasis",
            "Offers.Listings.Availability.Message",
            "Images.Primary.Large",
        ],
    )

    try:
        response = api.get_items(request)
        if response.items_result and response.items_result.products:
            return _parse_item(response.items_result.products[0], marketplace, cfg, "general")
    except ApiException as e:
        logger.error(f"Amazon PA-API GetItems Error ({marketplace.upper()}): {e}")
    return None


def _parse_item(product, marketplace: str, cfg: dict, category_slug: str) -> dict | None:
    try:
        asin = product.asin
        title = product.item_info.title.display_value if product.item_info and product.item_info.title else None
        if not title:
            return None

        # Brand
        brand = None
        if product.item_info and product.item_info.by_line_info and product.item_info.by_line_info.brand:
            brand = product.item_info.by_line_info.brand.display_value

        # Features (bullets)
        features = []
        if product.item_info and product.item_info.features and product.item_info.features.display_values:
            features = product.item_info.features.display_values

        # Image
        image_url = None
        if product.images and product.images.primary and product.images.primary.large:
            image_url = product.images.primary.large.url

        # Price & Availability
        price = None
        old_price = None
        availability = "Unknown"
        affiliate_url = product.detail_page_url

        if product.offers and product.offers.listings:
            listing = product.offers.listings[0]
            if listing.price:
                price = listing.price.amount
            if listing.saving_basis:
                old_price = listing.saving_basis.amount
            if listing.availability and listing.availability.message:
                availability = listing.availability.message

        return {
            "asin":           asin,
            "name":           title,
            "brand_name":     brand,
            "features":       features,
            "image_url":      image_url,
            "price":          price,
            "old_price":      old_price,
            "availability":   availability,
            "affiliate_url":  affiliate_url,
            "currency":       cfg["currency"],
            "country":        cfg["country"],
            "marketplace":    marketplace,
            "category_slug":  category_slug,
        }
    except Exception:
        logger.exception(f"Error parsing Amazon product {asin}")
        return None
