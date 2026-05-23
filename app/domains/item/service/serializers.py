"""Item serialization for templates and APIs."""

from app.domains.serializers import serialize_model


def serialize_store_link(link):
    """Serialize a single active store link.

    Exposes both ``store`` (nested object for Jinja templates) and flat
    ``name``/``logo``/``url`` keys that purchase-options.js expects so a
    single serializer satisfies every consumer.
    """
    if not link or not link.is_active:
        return None

    store = link.store
    store_data = (
        {"name": store.name, "logo_url": store.logo_url, "slug": store.slug}
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
        "logo": store.logo_url if store else None,
    }


def serialize_store_links(links):
    """Serialize a list of store links, skipping inactive ones."""
    return [row for row in (serialize_store_link(link) for link in links) if row]


def serialize_item_variant(variant, item=None):
    """Serialize an item variant.

    Images are merged (variant-specific first, then item-level) so that
    both the gallery and the variant-selector receive a unified flat URL list.
    ``images_detailed`` retains the full object list for templates that need
    position/id metadata.
    """
    if not variant:
        return None

    item_images = item.images if item else []
    variant_images = variant.images or []

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


def serialize_item(item):
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

    variant_data = [serialize_item_variant(v, item=item) for v in item.variants]

    return {
        "id": item.id,
        "name": item.name,
        "slug": item.slug,
        # Single canonical key — templates use item.item_type
        "item_type": item.item_type,
        "card_type": item.card_type,
        "brand": serialize_model(item.brand),
        "category": serialize_model(item.category),
        # Single canonical image key
        "image_url": item.image_url,
        "price": float(item.price) if item.price is not None else None,
        "min_price": float(item.min_price) if item.min_price is not None else None,
        "has_variants": item.has_variants,
        "default_variant": (
            {
                "id": default_variant.id,
                "sku": getattr(default_variant, "sku", None),
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
        "view_count": item.view_count,
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

    data = serialize_item(item)

    structured = item.structured_details
    groups = structured.get("groups") if structured else None

    detailed_images = [
        {"id": img.id, "image_url": img.image_url, "position": img.position}
        for img in item.images
    ]

    # O(N) — serialize each variant exactly once
    variants_detailed = [serialize_item_variant(v, item=item) for v in item.variants]

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
