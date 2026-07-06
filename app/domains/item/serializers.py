from typing import Optional, Dict, Any
from app.domains.serializers import serialize_model

def serialize_store_inspect_dto(store, stats, product_count, currency_mix_list, avg_sync_age) -> Optional[Dict[str, Any]]:
    """Serializes a Store ORM model and its aggregated stats into a DTO."""
    if not store:
        return None

    return {
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
        "active_links": getattr(stats, "active_links", 0) or 0,
        "inactive_links": getattr(stats, "inactive_links", 0) or 0,
        "total_links": getattr(stats, "total_links", 0) or 0,
        "never_synced": getattr(stats, "never_synced", 0) or 0,
        "stale_links": getattr(stats, "stale_links", 0) or 0,
        "out_of_stock": getattr(stats, "out_of_stock", 0) or 0,
        
        "avg_sync_age": avg_sync_age,
        "last_synced_at": stats.last_synced.isoformat() if stats and stats.last_synced else None,
        
        "program_count": getattr(stats, "program_count", 0) or 0,
        "avg_commission": float(stats.avg_commission) if stats and stats.avg_commission is not None else None,
        "max_commission": float(stats.max_commission) if stats and stats.max_commission is not None else None,
        "with_commission": getattr(stats, "with_commission", 0) or 0,
        "without_commission": getattr(stats, "without_commission", 0) or 0,
        "with_tracking": getattr(stats, "with_tracking", 0) or 0,
        
        "min_price": float(stats.min_price) if stats and stats.min_price is not None else None,
        "avg_price": float(stats.avg_price) if stats and stats.avg_price is not None else None,
        "max_price": float(stats.max_price) if stats and stats.max_price is not None else None,
        "with_discount": getattr(stats, "with_discount", 0) or 0,
        "avg_discount_pct": float(stats.avg_discount_pct) if stats and stats.avg_discount_pct is not None else None,
        "null_price": getattr(stats, "null_price", 0) or 0,
        
        "currency_mix": currency_mix_list
    }

def _build_inspect_store_links(item):
    store_links_data = []
    last_synced_dates = []
    
    for v in item.variants:
        for lnk in v.store_links:
            if lnk.last_synced_at:
                last_synced_dates.append(lnk.last_synced_at)
            elif lnk.last_checked_at:
                last_synced_dates.append(lnk.last_checked_at)
                
            store_links_data.append({
                "store_name": lnk.store.name if lnk.store else "—",
                "affiliate_network": lnk.store.affiliate_network if lnk.store else "—",
                "program_name": lnk.program_name or "—",
                "affiliate_url": lnk.affiliate_url or "—",
                "original_url": lnk.original_url or "—",
                "price": float(lnk.price) if lnk.price is not None else None,
                "old_price": float(lnk.old_price) if lnk.old_price is not None else None,
                "currency": lnk.currency,
                "availability": lnk.availability,
                "is_active": lnk.is_active,
                "last_synced_at": lnk.last_synced_at.isoformat() if lnk.last_synced_at else None,
                "last_checked_at": lnk.last_checked_at.isoformat() if lnk.last_checked_at else None,
                "merchant_category": lnk.merchant_category or "—",
                "external_item_id": lnk.external_item_id or "—",
                "metadata": lnk.network_metadata or {},
                "commission_rate": float(lnk.commission_rate) if lnk.commission_rate is not None else None,
            })
    return store_links_data, last_synced_dates

def _build_inspect_variant_summary(item):
    variant_summary = []
    for v in item.variants:
        variant_summary.append({
            "id": v.id,
            "sku": v.sku,
            "is_default": v.is_default,
            "attributes": v.attributes,
            "price": float(v.price) if v.price is not None else None,
            "old_price": float(v.old_price) if v.old_price is not None else None,
            "currency": v.currency,
            "store_links_count": len(v.store_links),
            "images_count": len(v.images)
        })
    return variant_summary

def _build_inspect_image_strip(item):
    image_strip = []
    for img in item.images:
        image_strip.append({
            "id": img.id,
            "url": img.image_url,
            "is_primary": img.position == 0,
            "variant_id": img.variant_id,
            "position": img.position
        })
    return image_strip

def _build_inspect_specifications(item):
    return {
        "structured_details": item.structured_details,
        "quick_details": item.quick_details,
        "searchable_attributes": item.searchable_attributes,
        "specs_list": [{"key": s.category, "value": s.spec_json} for s in item.specifications]
    }

def _build_inspect_comments(item):
    return [
        {
            "user_name": c.user.name if getattr(c, "user", None) else f"User #{c.user_id}",
            "content": c.content,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in item.comments
    ]

def serialize_item_inspect_dto(item) -> Optional[Dict[str, Any]]:
    """Serializes an Item ORM model and its eagerly loaded relations into a DTO."""
    if not item:
        return None

    store_links_data, last_synced_dates = _build_inspect_store_links(item)
    variant_summary = _build_inspect_variant_summary(item)
    image_strip = _build_inspect_image_strip(item)
    specifications = _build_inspect_specifications(item)
    recent_comments = _build_inspect_comments(item)

    return {
        "id": item.id,
        "name": item.name,
        "category_name": item.category.name if item.category else None,
        "brand_name": item.brand.name if item.brand else None,
        "source_name": item.source.name if getattr(item, "source", None) else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        
        "variants_count": len(item.variants),
        "store_count": len(store_links_data),
        "min_price": float(item.min_price) if item.min_price is not None else None,
        "variant_groups": item.variant_groups,
        
        "view_count": item.view_count or 0,
        "like_count": item.like_count or 0,
        "dislike_count": item.dislike_count or 0,
        "comment_count": item.comment_count or 0,
        "share_count": item.share_count or 0,
        "save_count": item.save_count or 0,
        "click_count": item.click_count or 0,
        
        "linked_contents_count": len(item.linked_contents),
        "description": item.description,
        "rating": item.rating,
        "review_count": item.review_count or 0,
        "images_count": len(item.images),
        "specs_count": len(item.specifications),
        
        "store_links": store_links_data,
        "last_synced_dates": [d.isoformat() for d in last_synced_dates],
        "variant_summary": variant_summary,
        "image_strip": image_strip,
        "specifications": specifications,
        "comments": recent_comments
    }

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

    return {
        "id": link.id,
        # Template key
        "affiliate_url": link.affiliate_url,
        # JS key (purchase-options.js reads `link.url`)
        "url": link.affiliate_url,
        "price": float(link.price) if link.price is not None else None,
        "old_price": float(link.old_price) if link.old_price is not None else None,
        "currency": link.currency,
        # Nested store object (Jinja templates)
        "store": store_data,
        # Flat keys (purchase-options.js reads `link.name` / `link.logo`)
        "name": store.name if store else "",
        "logo": serialize_asset_url(store_logo),
    }


def serialize_store_links(links):
    """Serialize a list of store links, skipping inactive ones."""
    return [row for row in (serialize_store_link(link) for link in links) if row]


def serialize_item_variant(variant, item=None, include_variant_images=True):
    """Serialize an item variant.

    Images are merged (variant-specific first, then item-level) so that
    both the gallery and the variant-selector receive a unified flat URL list.
    ``images_detailed`` retains the full object list for templates that need
    position/id metadata.
    """
    if not variant:
        return None

    item_images = item.images if item else []
    variant_images = list(variant.images or []) if include_variant_images else []

    seen: set = set()
    merged_images: list[str] = []
    for img in variant_images + list(item_images):
        url = img.image_url
        if url and url not in seen:
            seen.add(url)
            merged_images.append(url)

    return {
        "id": variant.id,
        "title": variant.title,
        "sku": variant.sku,
        "attributes": variant.attributes or {},
        "is_default": variant.is_default,
        "price": float(variant.price) if variant.price is not None else 0.0,
        "old_price": float(variant.old_price) if variant.old_price is not None else 0.0,
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
    }


def serialize_item(item, include_variant_images=False):
    """Serialize basic item info for catalog cards and related-items lists.

    Kept intentionally lean: only what cards and listing pages need.
    Full detail (specs, structured data, all variants) lives in
    ``serialize_item_detail``.
    """
    if not item:
        return None

    default_variant = item.default_variant
    store_links = (
        serialize_store_links(default_variant.store_links) if default_variant else []
    )

    variant_data = [
        serialize_item_variant(
            v, item=item, include_variant_images=include_variant_images
        )
        for v in item.variants
    ]

    return {
        "id": item.id,
        "name": item.name,
        "slug": item.slug,
        # Single canonical key — templates use item.item_type
        "item_type": item.item_type,
        "type": item.item_type,
        "card_type": item.card_type,
        "brand": serialize_model(item.brand),
        "category": serialize_model(item.category),
        "view_count": getattr(item, "view_count", 0),
        "comment_count": getattr(item, "comment_count", 0),
        # Single canonical image key
        "image_url": item.image_url,
        "price": float(item.price) if item.price is not None else None,
        "min_price": float(item.min_price) if item.min_price is not None else None,
        "has_variants": item.has_variants,
        "default_variant": (
            {
                "id": default_variant.id,
                "sku": getattr(default_variant, "sku", None),
                "currency": getattr(default_variant, "currency", None),
                "price": (
                    float(default_variant.price)
                    if default_variant.price is not None
                    else None
                ),
            }
            if default_variant
            else None
        ),
        "variant_data": variant_data,
        "variant_groups": item.variant_groups,
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
        "rating": item.rating,
        "review_count": item.review_count,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "badges": (
            item.pick_keys(item.searchable_attributes, ["badge", "tag"])
            if item.searchable_attributes
            else None
        ),
    }


def serialize_item_detail(item):
    """Serialize full item details including specs, all variants, and all images.

    Calls ``serialize_item`` for the base payload, then extends it with
    detail-only fields.  Each variant is serialized exactly once (O(N)).
    """
    if not item:
        return None

    data = serialize_item(item, include_variant_images=True)

    structured = item.structured_details
    groups = structured.get("groups") if structured else None

    detailed_images = [
        {"id": img.id, "image_url": img.image_url, "position": img.position}
        for img in item.images
    ]

    # Keep the explicit detail key for templates that read item.variants.
    variants_detailed = [
        serialize_item_variant(v, item=item, include_variant_images=True)
        for v in item.variants
    ]

    data.update(
        {
            "images": detailed_images,
            "variants": variants_detailed,
            "structured_details": structured,
            "quick_details": item.quick_details,
            "full_details": groups if isinstance(groups, dict) else item.full_details,
        }
    )
    return data

def _calculate_item_completeness_score(item, price_info, store_info, has_image, has_specs):
    completeness_points = 0
    total_criteria = 8
    if has_image: completeness_points += 1
    if item.brand_id: completeness_points += 1
    if item.description and len(item.description) > 10: completeness_points += 1
    if store_info.get("active_links", 0) > 0: completeness_points += 1
    if price_info.get("price") is not None: completeness_points += 1
    if has_specs: completeness_points += 1
    if item.searchable_attributes and len(item.searchable_attributes) > 0: completeness_points += 1
    if item.structured_details and len(item.structured_details) > 0: completeness_points += 1
    
    return int((completeness_points / total_criteria) * 100)

def serialize_item_row(item, price_info, store_info, has_image, has_specs):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    
    price_min = price_info.get("price")
    price_max = price_info.get("max_price")
    currency = price_info.get("currency")

    sync_age_days = None
    last_synced_at = store_info.get("last_synced_at")
    if last_synced_at:
        if last_synced_at.tzinfo is None:
            last_synced_at = last_synced_at.replace(tzinfo=timezone.utc)
        sync_age_days = (now - last_synced_at).days

    completeness_score = _calculate_item_completeness_score(item, price_info, store_info, has_image, has_specs)

    return {
        "id":          item.id,
        "name":        item.name,
        "slug":        item.slug,
        "image_url":   item.image_url if has_image else None,
        "brand":       item.brand.name if item.brand else "—",
        "brand_slug":  item.brand.slug if item.brand else None,
        "category":    item.category.name if item.category else "—",
        "category_slug": item.category.slug if item.category else None,
        "category_name": item.category.name if item.category else None,
        "brand_name":  item.brand.name if item.brand else None,
        "min_price":   price_min,
        "max_price":   price_max,
        "currency":    currency,
        "store_count": store_info.get("active_links", 0),
        "last_synced_at": store_info.get("last_synced_at").isoformat() if store_info.get("last_synced_at") else None,
        "sync_age":    sync_age_days,
        "has_discount": store_info.get("has_discount", False),
        "health":      completeness_score,
        "click_count": item.click_count or 0,
        "view_count":  item.view_count or 0,
        "created_at":  item.created_at.isoformat() if item.created_at else None,
    }

