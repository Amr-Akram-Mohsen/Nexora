from typing import Optional, Dict, Any

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

def serialize_item_inspect_dto(item) -> Optional[Dict[str, Any]]:
    """Serializes an Item ORM model and its eagerly loaded relations into a DTO."""
    if not item:
        return None

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

    image_strip = []
    for img in item.images:
        image_strip.append({
            "id": img.id,
            "url": img.image_url,
            "is_primary": img.position == 0,
            "variant_id": img.variant_id,
            "position": img.position
        })

    specifications = {
        "structured_details": item.structured_details,
        "quick_details": item.quick_details,
        "searchable_attributes": item.searchable_attributes,
        "specs_list": [{"key": s.category, "value": s.spec_json} for s in item.specifications]
    }

    recent_comments = [
        {
            "user_name": c.user.name if getattr(c, "user", None) else f"User #{c.user_id}",
            "content": c.content,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in item.comments
    ]

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
