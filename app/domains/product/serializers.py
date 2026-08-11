from typing import Optional, Dict, Any
from app.domains.serializers import serialize_model
from app.domains.serialization_utils import compact_dict, safe_float, safe_isoformat, safe_attr

def serialize_store_inspect_dto(store, stats, product_count, currency_mix_list, avg_sync_age) -> Optional[Dict[str, Any]]:
    """Serializes a Store ORM model and its aggregated stats into a DTO."""
    if not store:
        return None

    return compact_dict({
        "id": store.id,
        "name": store.name,
        "slug": store.slug,
        "website": store.website,
        "is_active": store.is_active,
        "affiliate_network": store.affiliate_network,
        "country": store.country,
        "currency": store.currency,
        "api_enabled": store.api_enabled,
        "feed_enabled": store.feed_enabled,
        "network_slug": store.network_slug,
        
        "product_count": product_count,
        "active_links": safe_attr(stats, "active_links", 0),
        "inactive_links": safe_attr(stats, "inactive_links", 0),
        "total_links": safe_attr(stats, "total_links", 0),
        "never_synced": safe_attr(stats, "never_synced", 0),
        "stale_links": safe_attr(stats, "stale_links", 0),
        "out_of_stock": safe_attr(stats, "out_of_stock", 0),
        
        "avg_sync_age": avg_sync_age,
        "last_synced_at": safe_isoformat(stats, "last_synced"),
        
        "program_count": safe_attr(stats, "program_count", 0),
        "avg_commission": safe_float(stats, "avg_commission"),
        "max_commission": safe_float(stats, "max_commission"),
        "with_commission": safe_attr(stats, "with_commission", 0),
        "without_commission": safe_attr(stats, "without_commission", 0),
        "with_tracking": safe_attr(stats, "with_tracking", 0),
        
        "min_price": safe_float(stats, "min_price"),
        "avg_price": safe_float(stats, "avg_price"),
        "max_price": safe_float(stats, "max_price"),
        "with_discount": safe_attr(stats, "with_discount", 0),
        "avg_discount_pct": safe_float(stats, "avg_discount_pct"),
        "null_price": safe_attr(stats, "null_price", 0),
        
        "currency_mix": currency_mix_list
    })

def _build_inspect_store_links(product):
    store_links_data = []
    last_synced_dates = []
    
    for v in product.variants:
        for lnk in v.store_links:
            if lnk.last_synced_at:
                last_synced_dates.append(lnk.last_synced_at)
            elif lnk.last_checked_at:
                last_synced_dates.append(lnk.last_checked_at)
                
            store_links_data.append(compact_dict({
                "store_name": lnk.store.name if lnk.store else "—",
                "affiliate_network": lnk.store.affiliate_network if lnk.store else "—",
                "program_name": lnk.program_name or "—",
                "affiliate_url": lnk.affiliate_url or "—",
                "original_url": lnk.original_url or "—",
                "price": safe_float(lnk, "price"),
                "old_price": safe_float(lnk, "old_price"),
                "currency": lnk.currency,
                "availability": lnk.availability,
                "is_active": lnk.is_active,
                "last_synced_at": safe_isoformat(lnk, "last_synced_at"),
                "last_checked_at": safe_isoformat(lnk, "last_checked_at"),
                "merchant_category": lnk.merchant_category or "—",
                "external_product_id": lnk.external_product_id or "—",
                "metadata": lnk.network_metadata or {},
                "commission_rate": safe_float(lnk, "commission_rate"),
            }))
    return store_links_data, last_synced_dates

def _build_inspect_variant_summary(product):
    variant_summary = []
    for v in product.variants:
        variant_summary.append(compact_dict({
            "id": v.id,
            "sku": v.sku,
            "is_default": v.is_default,
            "attributes": v.attributes,
            "price": safe_float(v, "price"),
            "old_price": safe_float(v, "old_price"),
            "currency": v.currency,
            "store_links_count": len(v.store_links),
            "images_count": len(v.images)
        }))
    return variant_summary

def _build_inspect_image_strip(product):
    image_strip = []
    for img in product.images:
        image_strip.append(compact_dict({
            "id": img.id,
            "url": img.image_url,
            "is_primary": img.position == 0,
            "variant_id": img.variant_id,
            "position": img.position
        }))
    return image_strip

def _build_inspect_specifications(product):
    return compact_dict({
        "structured_details": product.structured_details,
        "quick_details": product.quick_details,
        "searchable_attributes": product.searchable_attributes,
        "specs_list": [{"key": s.category, "value": s.spec_json} for s in product.specifications]
    })

def _build_inspect_comments(product):
    return [
        compact_dict({
            "user_name": c.user.name if getattr(c, "user", None) else f"User #{c.user_id}",
            "content": c.content,
            "created_at": safe_isoformat(c, "created_at")
        })
        for c in product.comments
    ]

def serialize_item_inspect_dto(product) -> Optional[Dict[str, Any]]:
    """Serializes an Product ORM model and its eagerly loaded relations into a DTO."""
    if not product:
        return None

    store_links_data, last_synced_dates = _build_inspect_store_links(product)
    variant_summary = _build_inspect_variant_summary(product)
    image_strip = _build_inspect_image_strip(product)
    specifications = _build_inspect_specifications(product)
    recent_comments = _build_inspect_comments(product)

    return compact_dict({
        "id": product.id,
        "name": product.name,
        "category_name": product.category.name if product.category else None,
        "brand_name": product.brand.name if product.brand else None,
        "source_name": product.source.name if getattr(product, "source", None) else None,
        "created_at": safe_isoformat(product, "created_at"),
        
        "variants_count": len(product.variants),
        "store_count": len(store_links_data),
        "min_price": safe_float(product, "min_price"),
        "variant_groups": product.variant_groups,
        
        "view_count": product.view_count or 0,
        "like_count": product.like_count or 0,
        "dislike_count": product.dislike_count or 0,
        "comment_count": product.comment_count or 0,
        "share_count": product.share_count or 0,
        "save_count": product.save_count or 0,
        "click_count": product.click_count or 0,
        
        "linked_contents_count": len(product.linked_contents),
        "description": product.description,
        "rating": product.rating,
        "review_count": product.review_count or 0,
        "images_count": len(product.images),
        "specs_count": len(product.specifications),
        
        "store_links": store_links_data,
        "last_synced_dates": [d.isoformat() for d in last_synced_dates],
        "variant_summary": variant_summary,
        "image_strip": image_strip,
        "specifications": specifications,
        "comments": recent_comments
    })

def serialize_asset_url(url):
    if not url:
        return None

    if url.startswith(("http://", "https://", "//", "/")):
        return url

    if url.startswith("static/"):
        return f"/{url}"

    return f"/static/{url}"


def serialize_store_link(link):
    """Serialize a single active store link.

    Exposes both ``store`` (nested object for Jinja templates) and flat
    ``name``/``logo``/``url`` keys that purchase-options.js expects so a
    single serializer satisfies every consumer.
    """
    if not link or not link.is_active:
        return None

    store = link.store
    store_logo = store.logo_url if store else None
    store_data = (
        {"name": store.name, "logo_url": store_logo, "slug": store.slug}
        if store
        else None
    )

    return compact_dict({
        "id": link.id,
        # Template key
        "affiliate_url": link.affiliate_url,
        # JS key (purchase-options.js reads `link.url`)
        "url": link.affiliate_url,
        "price": safe_float(link, "price"),
        "old_price": safe_float(link, "old_price"),
        "currency": link.currency,
        # Nested store object (Jinja templates)
        "store": store_data,
        # Flat keys (purchase-options.js reads `link.name` / `link.logo`)
        "name": store.name if store else "",
        "logo": serialize_asset_url(store_logo),
    })


def serialize_store_links(links):
    """Serialize a list of store links, skipping inactive ones."""
    return [row for row in (serialize_store_link(link) for link in links) if row]


def serialize_item_variant(variant, product=None, include_variant_images=True):
    """Serialize an product variant.

    Images are merged (variant-specific first, then product-level) so that
    both the gallery and the variant-selector receive a unified flat URL list.
    ``images_detailed`` retains the full object list for templates that need
    position/id metadata.
    """
    if not variant:
        return None

    product_images = product.images if product else []
    variant_images = list(variant.images or []) if include_variant_images else []

    seen: set = set()
    merged_images: list[str] = []
    for img in variant_images + list(product_images):
        url = img.image_url
        if url and url not in seen:
            seen.add(url)
            merged_images.append(url)

    return compact_dict({
        "id": variant.id,
        "title": variant.title,
        "sku": variant.sku,
        "attributes": variant.attributes or {},
        "is_default": variant.is_default,
        "price": safe_float(variant, "price", default=0.0),
        "old_price": safe_float(variant, "old_price", default=0.0),
        "currency": variant.currency,
        "display_name": variant.display_name(),
        # Primary image URL (gallery main image on variant switch)
        "image": merged_images[0] if merged_images else None,
        # Flat URL list — variant-selector.js / gallery.js
        "images": merged_images,
        # Detailed list — templates that need position / id
        "images_detailed": [
            {"id": img.id, "image_url": img.image_url, "position": img.position}
            for img in variant_images
        ],
        "store_links": serialize_store_links(variant.store_links),
    })


def serialize_item(product, include_variant_images=False):
    """Serialize basic product info for catalog cards and related-products lists.

    Kept intentionally lean: only what cards and listing pages need.
    Full detail (specs, structured data, all variants) lives in
    ``serialize_item_detail``.
    """
    if not product:
        return None

    default_variant = product.default_variant
    store_links = (
        serialize_store_links(default_variant.store_links) if default_variant else []
    )

    variant_data = [
        serialize_item_variant(
            v, product=product, include_variant_images=include_variant_images
        )
        for v in product.variants
    ]

    return compact_dict({
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        # Single canonical key — templates use product.product_type
        "product_type": product.product_type,
        "type": product.product_type,
        "card_type": product.card_type,
        "brand": serialize_model(product.brand),
        "category": serialize_model(product.category),
        "view_count": getattr(product, "view_count", 0),
        "comment_count": getattr(product, "comment_count", 0),
        # Single canonical image key
        "image_url": product.image_url,
        "price": safe_float(product, "price"),
        "min_price": safe_float(product, "min_price"),
        "has_variants": product.has_variants,
        "default_variant": (
            {
                "id": default_variant.id,
                "sku": getattr(default_variant, "sku", None),
                "currency": getattr(default_variant, "currency", None),
                "price": safe_float(default_variant, "price"),
            }
            if default_variant
            else None
        ),
        "variant_data": variant_data,
        "variant_groups": product.variant_groups,
        "store_links": store_links,
        # Convenience flat list for templates that iterate stores
        "stores": [
            {
                "name": link["store"]["name"] if link["store"] else "",
                "slug": link["store"]["slug"] if link["store"] else "",
                "price": link["price"],
                "currency": link["currency"],
            }
            for link in store_links
        ],
        "rating": product.rating,
        "review_count": product.review_count,
        "created_at": safe_isoformat(product.created_at),
        "badges": (
            product.pick_keys(product.searchable_attributes, ["badge", "tag"])
            if product.searchable_attributes
            else None
        ),
    })


def serialize_item_detail(product):
    """Serialize full product details including specs, all variants, and all images.

    Calls ``serialize_item`` for the base payload, then extends it with
    detail-only fields.  Each variant is serialized exactly once (O(N)).
    """
    if not product:
        return None

    data = serialize_item(product, include_variant_images=True)

    structured = product.structured_details
    groups = structured.get("groups") if structured else None

    detailed_images = [
        {"id": img.id, "image_url": img.image_url, "position": img.position}
        for img in product.images
    ]

    # Keep the explicit detail key for templates that read product.variants.
    variants_detailed = [
        serialize_item_variant(v, product=product, include_variant_images=True)
        for v in product.variants
    ]

    data.update(
        {
            "images": detailed_images,
            "variants": variants_detailed,
            "structured_details": structured,
            "quick_details": product.quick_details,
            "full_details": groups if isinstance(groups, dict) else product.full_details,
        }
    )
    return compact_dict(data)

def _calculate_item_completeness_score(product, price_info, store_info, has_image, has_specs):
    completeness_points = 0
    total_criteria = 8
    if has_image: completeness_points += 1
    if product.brand_id: completeness_points += 1
    if product.description and len(product.description) > 10: completeness_points += 1
    if store_info.get("active_links", 0) > 0: completeness_points += 1
    if price_info.get("price") is not None: completeness_points += 1
    if has_specs: completeness_points += 1
    if product.searchable_attributes and len(product.searchable_attributes) > 0: completeness_points += 1
    if product.structured_details and len(product.structured_details) > 0: completeness_points += 1
    
    return int((completeness_points / total_criteria) * 100)

def serialize_product_row(product, price_info, store_info, has_image, has_specs):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    
    price_min = price_info.get("price")
    price_max = price_info.get("max_price")
    currency = price_info.get("currency")

    sync_age_days = None
    last_synced_at = store_info.get("last_synced_at")
    # safe_isoformat from dict is possible, but we don't need safe_isoformat if it's already an iso string from store_info.
    # store_info might have a datetime object or a string. Wait, above store_info has iso strings.
    if last_synced_at:
        if last_synced_at.tzinfo is None:
            last_synced_at = last_synced_at.replace(tzinfo=timezone.utc)
        sync_age_days = (now - last_synced_at).days

    completeness_score = _calculate_item_completeness_score(product, price_info, store_info, has_image, has_specs)

    return compact_dict({
        "id":          product.id,
        "name":        product.name,
        "slug":        product.slug,
        "image_url":   product.image_url if has_image else None,
        "brand":       product.brand.name if product.brand else "—",
        "brand_slug":  product.brand.slug if product.brand else None,
        "category":    product.category.name if product.category else "—",
        "category_slug": product.category.slug if product.category else None,
        "category_name": product.category.name if product.category else None,
        "brand_name":  product.brand.name if product.brand else None,
        "min_price":   price_min,
        "max_price":   price_max,
        "currency":    currency,
        "store_count": store_info.get("active_links", 0),
        "last_synced_at": store_info.get("last_synced_at"), # already iso string
        "sync_age":    sync_age_days,
        "has_discount": store_info.get("has_discount", False),
        "health":      completeness_score,
        "click_count": product.click_count or 0,
        "view_count":  product.view_count or 0,
        "created_at":  safe_isoformat(product, "created_at"),
    })

